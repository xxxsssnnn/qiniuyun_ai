import asyncio
import uuid

from app.services.connection_manager import ConnectionManager


async def start_mock_stream(manager: ConnectionManager, session_id: str) -> None:
    samples = [
        {
            "type": "chunk",
            "payload": {
                "chunk_id": str(uuid.uuid4()),
                "session_id": session_id,
                "source_text": "Welcome everyone to this technical talk.",
                "translated_text": "欢迎大家来到这场技术分享。",
                "is_final": False,
                "start_ms": 0,
                "end_ms": 1800,
                "revision": 0,
            },
        },
        {
            "type": "translated",
            "payload": {
                "chunk_id": str(uuid.uuid4()),
                "session_id": session_id,
                "source_text": "Today we will discuss real-time translation architecture.",
                "translated_text": "今天我们将讨论实时翻译架构。",
                "is_final": False,
                "start_ms": 1800,
                "end_ms": 4200,
                "revision": 0,
            },
        },
        {
            "type": "revision",
            "payload": {
                "chunk_id": str(uuid.uuid4()),
                "session_id": session_id,
                "source_text": "Today we will discuss real-time interpretation architecture.",
                "translated_text": "今天我们将讨论实时同传架构。",
                "is_final": True,
                "start_ms": 1800,
                "end_ms": 4200,
                "revision": 1,
            },
        },
    ]

    for sample in samples:
        await manager.broadcast(session_id, sample)
        await asyncio.sleep(1.2)
