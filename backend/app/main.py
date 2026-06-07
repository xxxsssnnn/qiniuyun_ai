from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.database import Base, engine, ensure_transcript_translation_columns
from app.models.transcript import TranscriptRecord  # noqa: F401
from app.models.transcript_revision import TranscriptRevision  # noqa: F401
from app.models.transcript_session import TranscriptSession  # noqa: F401
from app.services.asr_factory import get_asr_provider
from app.services.audio_session import audio_sessions
from app.services.connection_manager import ConnectionManager
from app.services.glossary import glossary_manager
from app.services.mock_stream import start_mock_stream
from app.services.revision_manager import revision_manager
from app.services.realtime_pipeline import RealtimePipeline
from app.services.runtime_settings import load_runtime_settings
from app.services.streaming import TranscriptBuffer
from app.services.transcription_processor import TranscriptionProcessor
from app.services.translation_factory import get_translation_provider
from app.services.tts_factory import get_tts_provider

manager = ConnectionManager()
buffer = TranscriptBuffer()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_transcript_translation_columns()
    with engine.begin() as connection:
        glossary_manager.load_entries_from_db(connection)
    load_runtime_settings()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.websocket("/api/v1/transcripts/ws/{session_id}")
async def websocket_transcripts(websocket: WebSocket, session_id: str) -> None:
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


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
