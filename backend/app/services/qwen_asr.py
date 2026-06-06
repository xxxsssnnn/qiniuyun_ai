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


LANGUAGE_NAMES = {
    "zh": "中文",
    "en": "英语",
    "yue": "粤语",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "pt": "葡萄牙语",
    "it": "意大利语",
    "ar": "阿拉伯语",
    "th": "泰语",
    "vi": "越南语",
}


@dataclass
class QwenRealtimeSession:
    websocket: Any
    language: str
    results: asyncio.Queue[ASRResult] = field(default_factory=asyncio.Queue)
    reader_task: asyncio.Task[None] | None = None
    source_text: str = ""
    translated_text: str = ""


class QwenASRProvider(ASRProvider):
    def __init__(self) -> None:
        self.api_key = (
            os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("QWEN_API_KEY")
            or os.getenv("ALIYUN_API_KEY")
            or ""
        )
        configured_model = os.getenv("QWEN_ASR_MODEL", "qwen3.5-omni-plus-realtime")
        self.model = (
            "qwen3.5-omni-plus-realtime"
            if configured_model == "qwen3-asr-flash-realtime"
            else configured_model
        )
        self.language = os.getenv("QWEN_ASR_LANGUAGE", "en")
        self.target_language = os.getenv("TARGET_LANGUAGE", "zh")
        self.region = os.getenv("DASHSCOPE_REGION", "cn").lower()
        self.workspace_id = os.getenv("DASHSCOPE_WORKSPACE_ID", "")
        self._sessions: dict[str, QwenRealtimeSession] = {}
        self._session_lock = asyncio.Lock()

    @property
    def base_url(self) -> str:
        if self.region in {"intl", "international", "sg", "singapore"}:
            if not self.workspace_id:
                raise RuntimeError("DASHSCOPE_WORKSPACE_ID is required for the international region")
            return f"wss://{self.workspace_id}.ap-southeast-1.maas.aliyuncs.com/api-ws/v1/realtime"
        return "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"

    async def _read_events(self, session: QwenRealtimeSession) -> None:
        try:
            async for raw_message in session.websocket:
                event = json.loads(raw_message)
                event_type = event.get("type", "")
                if event_type == "conversation.item.input_audio_transcription.delta":
                    session.source_text = (
                        str(event.get("text", ""))
                        + str(event.get("stash", ""))
                    ).strip()
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    text = str(event.get("transcript", "")).strip()
                    if text:
                        session.source_text = text
                elif event_type in {"response.text.delta", "response.audio_transcript.delta"}:
                    delta = str(event.get("delta", ""))
                    if delta:
                        session.translated_text += delta
                        await session.results.put(
                            ASRResult(
                                text=session.source_text,
                                translated_text=session.translated_text,
                                is_final=False,
                                confidence=1.0,
                                language=session.language,
                            )
                        )
                elif event_type in {"response.text.done", "response.audio_transcript.done"}:
                    translated = str(event.get("text") or event.get("transcript") or session.translated_text).strip()
                    if translated:
                        await session.results.put(
                            ASRResult(
                                text=session.source_text,
                                translated_text=translated,
                                is_final=True,
                                confidence=1.0,
                                language=session.language,
                            )
                        )
                    session.source_text = ""
                    session.translated_text = ""
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
        target_language_name = LANGUAGE_NAMES.get(
            self.target_language,
            self.target_language,
        )
        await websocket.send(
            json.dumps(
                {
                    "event_id": f"event_{uuid.uuid4().hex}",
                    "type": "session.update",
                    "session": {
                        "modalities": ["text"],
                        "input_audio_format": "pcm",
                        "input_audio_transcription": {
                            "model": "qwen3-asr-flash-realtime",
                            "language": self.language,
                        },
                        "instructions": (
                            f"你是实时同声传译引擎。识别用户语音后，将其忠实、完整、简洁地翻译成{target_language_name}。"
                            f"只输出{target_language_name}译文，不回答问题，不解释，不添加标题、引号或额外内容。"
                            "保留人名、产品名、数字和专业术语的准确含义。"
                        ),
                        "temperature": 0.2,
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.3,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 500,
                            "create_response": True,
                            "interrupt_response": True,
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
                return ASRResult(text="", translated_text="", language=self.language)
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
