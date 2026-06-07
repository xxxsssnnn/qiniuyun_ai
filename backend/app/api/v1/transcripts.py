from typing import Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field

from app.services.transcript_store import transcript_store

from app.schemas.common import TranscriptChunkCreate, TranscriptChunkRead
from app.schemas.realtime import StreamTextChunk
from app.services.audio_session import audio_sessions
from app.services.asr_factory import get_asr_provider
from app.services.connection_manager import ConnectionManager
from app.services.mock_stream import start_mock_stream
from app.services.revision_manager import CorrectionEvent, revision_manager
from app.services.realtime_pipeline import RealtimePipeline
from app.services.streaming import TranscriptBuffer, TranscriptChunk
from app.services.transcription_processor import TranscriptionProcessor
from app.services.translation_factory import get_translation_provider
from app.services.tts_factory import get_tts_provider

router = APIRouter()
buffer = TranscriptBuffer()
manager = ConnectionManager()


class SessionCreate(BaseModel):
    name: str = Field(default="新会话", max_length=160)


class SessionUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)


class RollbackRequest(BaseModel):
    revision: int = Field(ge=0)


@router.post("/chunks", response_model=TranscriptChunkRead)
async def create_chunk(payload: TranscriptChunkCreate) -> TranscriptChunkRead:
    chunk = TranscriptChunk(
        chunk_id=payload.chunk_id,
        source_text=payload.source_text,
        translated_text=payload.translated_text or "",
        is_final=payload.is_final,
        revision=0,
    )
    buffer.append(chunk)
    transcript_store.save_chunk(chunk)
    return TranscriptChunkRead.model_validate(chunk)


@router.get("/latest", response_model=Optional[TranscriptChunkRead])
async def latest_chunk(session_id: str | None = None) -> Optional[TranscriptChunkRead]:
    latest = buffer.latest(session_id) or transcript_store.latest_chunk(session_id)
    return TranscriptChunkRead.model_validate(latest) if latest else None


@router.post("/stream", response_model=StreamTextChunk)
async def stream_chunk(payload: StreamTextChunk) -> StreamTextChunk:
    chunk = TranscriptChunk(
        chunk_id=payload.chunk_id,
        source_text=payload.source_text,
        translated_text=payload.translated_text,
        is_final=payload.is_final,
        session_id=payload.session_id,
        revision=payload.revision,
    )
    buffer.append(chunk)
    transcript_store.save_chunk(chunk)
    return payload


@router.get("/sessions")
async def list_sessions() -> list[dict]:
    return [summary.__dict__ for summary in transcript_store.list_sessions()]


@router.post("/sessions")
async def create_session(payload: SessionCreate) -> dict:
    session_id = f"session-{uuid4().hex}"
    return transcript_store.create_session(session_id, payload.name).__dict__


@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, payload: SessionUpdate) -> dict:
    session = transcript_store.rename_session(session_id, payload.name)
    return session.__dict__ if session else {}


@router.get("/sessions/{session_id}/chunks", response_model=list[TranscriptChunkRead])
async def list_session_chunks(session_id: str, final_only: bool = True) -> list[TranscriptChunkRead]:
    chunks = buffer.list_session(session_id, final_only=final_only) or transcript_store.list_chunks(session_id, final_only=final_only)
    return [TranscriptChunkRead.model_validate(chunk) for chunk in chunks]


@router.get(
    "/sessions/{session_id}/revisions",
    response_model=list[TranscriptChunkRead],
)
async def list_session_revisions(
    session_id: str,
    chunk_id: str | None = None,
) -> list[TranscriptChunkRead]:
    revisions = transcript_store.list_revisions(session_id, chunk_id)
    return [TranscriptChunkRead.model_validate(chunk) for chunk in revisions]


@router.post(
    "/sessions/{session_id}/chunks/{chunk_id}/rollback",
    response_model=TranscriptChunkRead,
)
async def rollback_chunk(
    session_id: str,
    chunk_id: str,
    payload: RollbackRequest,
) -> TranscriptChunkRead:
    history = transcript_store.list_revisions(session_id, chunk_id)
    target = next(
        (item for item in history if item.revision == payload.revision),
        None,
    )
    latest = next(
        (
            item
            for item in transcript_store.list_chunks(
                session_id,
                final_only=False,
            )
            if item.chunk_id == chunk_id
        ),
        None,
    )
    if target is None or latest is None:
        raise HTTPException(status_code=404, detail="Revision not found")

    restored = TranscriptChunk(
        chunk_id=chunk_id,
        source_text=target.source_text,
        translated_text=target.translated_text,
        is_final=target.is_final,
        session_id=session_id,
        revision=latest.revision + 1,
        auto_correction=True,
        correction_reasons=[f"手动回滚至 revision {target.revision}"],
    )
    buffer.upsert(restored)
    transcript_store.save_chunk(restored)
    revision_manager.record(restored, restored.revision)
    event = revision_manager.correction_payload(
        CorrectionEvent(
            chunk_id=restored.chunk_id,
            previous_revision=latest.revision,
            current_revision=restored.revision,
            source_text=restored.source_text,
            translated_text=restored.translated_text,
            is_final=restored.is_final,
        )
    )
    event["session_id"] = session_id
    event["payload"]["revision"] = restored.revision
    event["payload"]["autoCorrection"] = True
    event["payload"]["reasons"] = restored.correction_reasons
    await manager.broadcast(session_id, event)
    return TranscriptChunkRead.model_validate(restored)


@router.get("/sessions/{session_id}/export", response_model=None)
async def export_session(session_id: str, format: str = "json"):
    normalized_format = format.lower()
    exported = transcript_store.export_session(session_id, normalized_format)
    if normalized_format == "srt":
        return Response(
            content=str(exported),
            media_type="application/x-subrip; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{session_id}.srt"'},
        )
    if normalized_format == "txt":
        return Response(
            content=str(exported),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{session_id}.txt"'},
        )
    return exported if isinstance(exported, list) else []


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    processor = TranscriptionProcessor(
        manager,
        buffer,
        get_asr_provider(),
        get_translation_provider(),
        get_tts_provider(),
    )
    await manager.connect(session_id, websocket)
    session = audio_sessions.get_or_create(session_id)
    pipeline: RealtimePipeline | None = None
    try:
        await manager.broadcast(session_id, {"type": "status", "session_id": session_id, "payload": {"message": "connected"}})
        while True:
            data = await websocket.receive()
            if data["type"] == "websocket.disconnect":
                break
            if data.get("text"):
                import json

                message = json.loads(data["text"])
                message_type = message.get("type")
                if message_type == "start_demo":
                    await manager.broadcast(session_id, {"type": "status", "session_id": session_id, "payload": {"message": "demo started"}})
                    await start_mock_stream(manager, session_id)
                elif message_type == "start_audio":
                    session.start()
                    if pipeline is None:
                        pipeline = RealtimePipeline(processor, session_id)
                        await pipeline.start()
                    await manager.broadcast(session_id, {"type": "audio", "session_id": session_id, "payload": {"message": "audio recording started"}})
                elif message_type == "stop_audio":
                    session.stop()
                    if pipeline is not None:
                        await pipeline.close()
                        pipeline = None
                    await manager.broadcast(session_id, {"type": "audio", "session_id": session_id, "payload": {"message": "audio recording stopped"}})
                elif message_type == "rollback":
                    chunk_id = message.get("chunk_id")
                    revision = int(message.get("revision", 0))
                    if chunk_id:
                        correction = revision_manager.rollback(chunk_id, revision)
                        if correction:
                            await manager.broadcast(session_id, revision_manager.correction_payload(correction))
                else:
                    await manager.broadcast(session_id, message)
            elif data.get("bytes"):
                session.append_chunk(data["bytes"])
                if pipeline is None:
                    pipeline = RealtimePipeline(processor, session_id)
                    await pipeline.start()
                await pipeline.enqueue_audio(data["bytes"])
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(session_id, websocket)
        if pipeline is not None:
            await pipeline.close()
        else:
            await processor.close_session(session_id)
