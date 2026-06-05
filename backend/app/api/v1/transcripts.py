from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas.common import TranscriptChunkCreate, TranscriptChunkRead
from app.schemas.realtime import StreamTextChunk
from app.services.connection_manager import ConnectionManager
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


@router.get("/latest", response_model=TranscriptChunkRead | None)
async def latest_chunk() -> TranscriptChunkRead | None:
    latest = buffer.latest()
    return TranscriptChunkRead.model_validate(latest) if latest else None


@router.post("/stream", response_model=StreamTextChunk)
async def stream_chunk(payload: StreamTextChunk) -> StreamTextChunk:
    return payload


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(session_id, data)
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
