from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.common import TranscriptChunkCreate, TranscriptChunkRead
from app.schemas.realtime import StreamTextChunk
from app.services.audio_session import audio_sessions
from app.services.asr import MockASRProvider
from app.services.connection_manager import ConnectionManager
from app.services.mock_stream import start_mock_stream
from app.services.streaming import TranscriptBuffer, TranscriptChunk
from app.services.transcription_processor import TranscriptionProcessor

router = APIRouter()
buffer = TranscriptBuffer()
manager = ConnectionManager()
processor = TranscriptionProcessor(manager, buffer, MockASRProvider())


@router.post("/chunks", response_model=TranscriptChunkRead)
async def create_chunk(payload: TranscriptChunkCreate) -> TranscriptChunkRead:
    chunk = TranscriptChunk(
        chunk_id=payload.chunk_id,
        source_text=payload.source_text,
        translated_text=payload.translated_text or "",
        is_final=payload.is_final,
    )
    buffer.append(chunk)
    return TranscriptChunkRead.model_validate(chunk)


@router.get("/latest", response_model=Optional[TranscriptChunkRead])
async def latest_chunk() -> Optional[TranscriptChunkRead]:
    latest = buffer.latest()
    return TranscriptChunkRead.model_validate(latest) if latest else None


@router.post("/stream", response_model=StreamTextChunk)
async def stream_chunk(payload: StreamTextChunk) -> StreamTextChunk:
    buffer.append(
        TranscriptChunk(
            chunk_id=payload.chunk_id,
            source_text=payload.source_text,
            translated_text=payload.translated_text,
            is_final=payload.is_final,
        )
    )
    return payload


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await manager.connect(session_id, websocket)
    session = audio_sessions.get_or_create(session_id)
    try:
        await manager.broadcast(session_id, {"type": "status", "session_id": session_id, "payload": {"message": "connected"}})
        while True:
            data = await websocket.receive()
            if data.get("text"):
                import json

                message = json.loads(data["text"])
                message_type = message.get("type")
                if message_type == "start_demo":
                    await manager.broadcast(session_id, {"type": "status", "session_id": session_id, "payload": {"message": "demo started"}})
                    await start_mock_stream(manager, session_id)
                elif message_type == "start_audio":
                    session.start()
                    await manager.broadcast(session_id, {"type": "audio", "session_id": session_id, "payload": {"message": "audio recording started"}})
                elif message_type == "stop_audio":
                    session.stop()
                    await manager.broadcast(session_id, {"type": "audio", "session_id": session_id, "payload": {"message": "audio recording stopped"}})
                else:
                    await manager.broadcast(session_id, message)
            elif data.get("bytes"):
                session.append_chunk(data["bytes"])
                await processor.handle_audio_chunk(session_id, data["bytes"])
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
