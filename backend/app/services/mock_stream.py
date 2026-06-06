import asyncio
import uuid

from app.services.connection_manager import ConnectionManager


async def start_mock_stream(manager: ConnectionManager, session_id: str) -> None:
    opening_id = str(uuid.uuid4())
    architecture_id = str(uuid.uuid4())
    samples = [
        {
            "type": "chunk",
            "payload": {
                "chunk_id": opening_id,
                "session_id": session_id,
                "sourceText": "Welcome everyone to this technical talk.",
                "translatedText": "欢迎大家来到这场技术分享。",
                "isFinal": False,
                "startMs": 0,
                "endMs": 1800,
                "revision": 0,
            },
        },
        {
            "type": "revision",
            "payload": {
                "chunk_id": opening_id,
                "session_id": session_id,
                "sourceText": "Welcome everyone to this technical talk about AI interpretation.",
                "translatedText": "欢迎大家来到这场关于 AI 同声传译的技术分享。",
                "isFinal": True,
                "startMs": 0,
                "endMs": 2600,
                "revision": 1,
            },
        },
        {
            "type": "chunk",
            "payload": {
                "chunk_id": architecture_id,
                "session_id": session_id,
                "sourceText": "Today we will discuss real-time translation architecture.",
                "translatedText": "今天我们将讨论实时翻译架构。",
                "isFinal": False,
                "startMs": 2600,
                "endMs": 5200,
                "revision": 0,
            },
        },
        {
            "type": "correction",
            "payload": {
                "chunk_id": architecture_id,
                "session_id": session_id,
                "previousRevision": 0,
                "currentRevision": 1,
                "sourceText": "Today we will discuss real-time interpretation architecture.",
                "translatedText": "今天我们将讨论实时同传架构。",
                "isFinal": True,
                "revision": 1,
            },
        },
    ]

    for sample in samples:
        await manager.broadcast(session_id, sample)
        await asyncio.sleep(1.2)
