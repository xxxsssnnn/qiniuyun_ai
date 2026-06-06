from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any

import websockets

from app.services.asr import ASRProvider, ASRResult


@dataclass
class QwenRealtimeSession:
    websocket: Any
    language: str
    results: asyncio.Queue[ASRResult] = field(default_factory=asyncio.Queue)
    reader_task: asyncio.Task[None] | None = None


class QwenASRProvider(ASRProvider):
    def __init__(self) -> None:
        self.api_key = (
            os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("QWEN_API_KEY")
            or os.getenv("ALIYUN_API_KEY")
            or ""
        )
        self.model = os.getenv("QWEN_ASR_MODEL", "qwen3-asr-flash-realtime")
        self.language = os.getenv("QWEN_ASR_LANGUAGE", "en")
        self.region = os.getenv("DASHSCOPE_REGION", "cn").lower()
        self._sessions: dict[str, QwenRealtimeSession] = {}
        self._session_lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        if self.region in {"intl", "international", "sg", "singapore"}:
            return "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"
        return "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"

    async def _read_events(self, session: QwenRealtimeSession) -> None:
        try:
            async for raw_message in session.websocket:
                event = json.loads(raw_message)
                event_type = event.get("type", "")
                if event_type == "conversation.item.input_audio_transcription.completed":
                    text = str(event.get("transcript", "")).strip()
                    if text:
                        await session.results.put(
                            ASRResult(
                                text=text,
                                is_final=True,
                                confidence=1.0,
                                language=session.language,
                            )
                        )
                elif event_type == "conversation.item.input_audio_transcription.text":
                    text = str(event.get("stash") or event.get("transcript") or "").strip()
                    if text:
                        await session.results.put(
                            ASRResult(
                                text=text,
                                is_final=False,
                                confidence=0.9,
                                language=session.language,
                            )
                        )
                elif event_type == "error":
                    error = event.get("error", {})
                    message = error.get("message", "Qwen realtime ASR error")
                    await session.results.put(
                        ASRResult(
                            text=f"[Qwen ASR error] {message}",
                            is_final=True,
                            language=session.language,
                        )
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await session.results.put(
                ASRResult(
                    text=f"[Qwen ASR connection error] {exc}",
                    is_final=True,
                    language=session.language,
                )
            )

    async def _create_session(self) -> QwenRealtimeSession:
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")

        websocket = await websockets.connect(
            f"{self.base_url}?model={self.model}",
            additional_headers={"Authorization": f"Bearer {self.api_key}"},
            open_timeout=10,
            ping_interval=20,
            ping_timeout=20,
            max_size=4 * 1024 * 1024,
        )
        session = QwenRealtimeSession(websocket=websocket, language=self.language)
        session.reader_task = asyncio.create_task(self._read_events(session))
        await websocket.send(
            json.dumps(
                {
                    "event_id": f"event_{uuid.uuid4().hex}",
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "input_audio_format": "pcm",
                        "sample_rate": 16000,
                        "input_audio_transcription": {"language": self.language},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.0,
                            "silence_duration_ms": 400,
                        },
                    },
                }
            )
        )
        return session

    async def _get_session(self, session_id: str) -> QwenRealtimeSession:
        current = self._sessions.get(session_id)
        if current and current.reader_task and not current.reader_task.done():
            return current

        async with self._session_lock:
            current = self._sessions.get(session_id)
            if current and current.reader_task and not current.reader_task.done():
                return current
            current = await self._create_session()
            self._sessions[session_id] = current
            return current

    async def test_connection(self) -> None:
        session = await self._create_session()
        await session.websocket.send(
            json.dumps(
                {
                    "event_id": f"event_{uuid.uuid4().hex}",
                    "type": "session.finish",
                }
            )
        )
        await session.websocket.close()
        if session.reader_task:
            session.reader_task.cancel()

    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        try:
            session = await self._get_session(session_id)
            await session.websocket.send(
                json.dumps(
                    {
                        "event_id": f"event_{uuid.uuid4().hex}",
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(audio_chunk).decode("ascii"),
                    }
                )
            )
            try:
                return await asyncio.wait_for(session.results.get(), timeout=0.08)
            except asyncio.TimeoutError:
                return ASRResult(text="", language=self.language)
        except Exception as exc:
            return ASRResult(
                text=f"[Qwen ASR unavailable] {exc}",
                is_final=True,
                language=self.language,
            )

    async def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if not session:
            return
        try:
            await session.websocket.send(
                json.dumps(
                    {
                        "event_id": f"event_{uuid.uuid4().hex}",
                        "type": "session.finish",
                    }
                )
            )
        except Exception:
            pass
        await session.websocket.close()
        if session.reader_task:
            session.reader_task.cancel()
