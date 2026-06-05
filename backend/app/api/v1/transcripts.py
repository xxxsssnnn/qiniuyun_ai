from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.common import TranscriptChunkCreate, TranscriptChunkRead
from app.schemas.realtime import StreamTextChunk
from app.services.connection_manager import ConnectionManager
from app.services.mock_stream import start_mock_stream
from app.services.streaming import TranscriptBuffer, TranscriptChunk

router = APIRouter()
buffer = TranscriptBuffer()
manager = ConnectionManager()


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
    try:
        await manager.broadcast(
            session_id,
            {
                "type": "status",
                "session_id": session_id,
                "payload": {"message": "connected"},
            },
        )
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "start_demo":
                await manager.broadcast(
                    session_id,
                    {
                        "type": "status",
                        "session_id": session_id,
                        "payload": {"message": "demo started"},
                    },
                )
                await start_mock_stream(manager, session_id)
            else:
                await manager.broadcast(session_id, data)
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
