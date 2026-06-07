from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

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


def _bounded_int_env(
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def _bounded_float_env(
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


@dataclass
class QwenRealtimeSession:
    websocket: Any
    language: str
    results: asyncio.Queue[ASRResult] = field(
        default_factory=lambda: asyncio.Queue(maxsize=32)
    )
    reader_task: asyncio.Task[None] | None = None
    source_text: str = ""
    completed_source_texts: deque[str] = field(default_factory=deque)
    active_response_source_text: str = ""
    response_active: bool = False
    translated_text: str = ""
    pending_partial: ASRResult | None = None
    finished: bool = False
    finish_requested: bool = False
    finish_confirmed: asyncio.Event = field(default_factory=asyncio.Event)
    closed: asyncio.Event = field(default_factory=asyncio.Event)


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
        self.vad_silence_duration_ms = _bounded_int_env(
            "QWEN_VAD_SILENCE_MS",
            default=900,
            minimum=500,
            maximum=3000,
        )
        self.vad_threshold = _bounded_float_env(
            "QWEN_VAD_THRESHOLD",
            default=0.1,
            minimum=0.1,
            maximum=0.9,
        )
        self.vad_prefix_padding_ms = _bounded_int_env(
            "QWEN_VAD_PREFIX_PADDING_MS",
            default=500,
            minimum=100,
            maximum=1000,
        )
        self.finish_timeout_seconds = _bounded_float_env(
            "QWEN_FINISH_TIMEOUT_SECONDS",
            default=4.0,
            minimum=1.0,
            maximum=10.0,
        )
        self._sessions: dict[str, QwenRealtimeSession] = {}
        self._session_lock = asyncio.Lock()

    @property
    def vad_type(self) -> str:
        configured_type = os.getenv("QWEN_VAD_TYPE", "").strip().lower()
        supports_semantic_vad = self.model.startswith("qwen3.5-omni")
        if configured_type == "server_vad":
            return configured_type
        if configured_type == "semantic_vad" and supports_semantic_vad:
            return configured_type
        return "semantic_vad" if supports_semantic_vad else "server_vad"

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
                if event_type == "conversation.item.input_audio_transcription.delta":
                    session.source_text = (
                        str(event.get("text", ""))
                        + str(event.get("stash", ""))
                    ).strip()
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    text = str(event.get("transcript", "")).strip()
                    if text:
                        if (
                            session.response_active
                            and not session.active_response_source_text
                        ):
                            session.active_response_source_text = text
                        else:
                            session.completed_source_texts.append(text)
                    session.source_text = ""
                elif event_type == "response.created":
                    session.response_active = True
                    session.translated_text = ""
                    if (
                        not session.active_response_source_text
                        and session.completed_source_texts
                    ):
                        session.active_response_source_text = (
                            session.completed_source_texts.popleft()
                        )
                elif event_type in {"response.text.delta", "response.audio_transcript.delta"}:
                    delta = str(event.get("delta", ""))
                    if delta:
                        session.translated_text += delta
                        partial = ASRResult(
                            text=(
                                session.active_response_source_text
                                or session.source_text
                            ),
                            translated_text=session.translated_text,
                            is_final=False,
                            confidence=1.0,
                            language=session.language,
                        )
                        session.pending_partial = partial
                        if session.results.empty():
                            await session.results.put(partial)
                elif event_type in {"response.text.done", "response.audio_transcript.done"}:
                    translated = str(event.get("text") or event.get("transcript") or session.translated_text).strip()
                    source_text = session.active_response_source_text
                    if not source_text and session.completed_source_texts:
                        source_text = session.completed_source_texts.popleft()
                    if translated:
                        await session.results.put(
                            ASRResult(
                                text=source_text,
                                translated_text=translated,
                                is_final=True,
                                confidence=1.0,
                                language=session.language,
                            )
                        )
                    session.pending_partial = None
                    session.translated_text = ""
                elif event_type == "response.done":
                    session.response_active = False
                    session.active_response_source_text = ""
                    session.translated_text = ""
                elif event_type == "session.finished" and session.finish_requested:
                    session.finish_confirmed.set()
                elif event_type == "error":
                    error = event.get("error", {})
                    message = error.get("message", "Qwen realtime ASR error")
                    await session.results.put(
                        ASRResult(
                            text="",
                            translated_text="",
                            is_final=False,
                            confidence=0.0,
                            language=session.language,
                            revision=0,
                        )
                    )
                    if session.finish_requested:
                        session.finish_confirmed.set()
        except asyncio.CancelledError:
            raise
        except ConnectionClosed as exc:
            if not session.finished:
                await session.results.put(
                    ASRResult(
                        text=(
                            "[Qwen connection closed] "
                            f"code={exc.code}, reason={exc.reason or 'unknown'}"
                        ),
                        is_final=True,
                        language=session.language,
                    )
                )
        except Exception as exc:
            await session.results.put(
                ASRResult(
                    text=f"[Qwen ASR connection error] {exc}",
                    is_final=True,
                    language=session.language,
                )
            )
        finally:
            session.closed.set()

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
                        "temperature": 0.0,
                        "turn_detection": self.turn_detection_config(),
                    },
                }
            )
        )
        return session

    def turn_detection_config(self) -> dict[str, Any]:
        return {
            "type": self.vad_type,
            "threshold": self.vad_threshold,
            "prefix_padding_ms": self.vad_prefix_padding_ms,
            "silence_duration_ms": self.vad_silence_duration_ms,
            "create_response": True,
            "interrupt_response": True,
        }

    async def _get_session(self, session_id: str) -> QwenRealtimeSession:
        current = self._sessions.get(session_id)
        if (
            current
            and not current.finished
            and current.reader_task
            and not current.reader_task.done()
        ):
            return current

        async with self._session_lock:
            current = self._sessions.get(session_id)
            if (
                current
                and not current.finished
                and current.reader_task
                and not current.reader_task.done()
            ):
                return current
            if current:
                await self._dispose_session(current)
            current = await self._create_session()
            self._sessions[session_id] = current
            return current

    async def _dispose_session(self, session: QwenRealtimeSession) -> None:
        if session.reader_task and not session.reader_task.done():
            session.reader_task.cancel()
            try:
                await session.reader_task
            except asyncio.CancelledError:
                pass
        try:
            await session.websocket.close()
        except Exception:
            pass

    async def test_connection(self) -> None:
        session = await self._create_session()
        session.finished = True
        await session.websocket.close()
        if session.reader_task:
            session.reader_task.cancel()

    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        await self.send_audio(audio_chunk, session_id)
        session = await self._get_session(session_id)
        try:
            return session.results.get_nowait()
        except asyncio.QueueEmpty:
            return ASRResult(text="", translated_text="", language=self.language)

    async def send_audio(self, audio_chunk: bytes, session_id: str) -> None:
        payload = json.dumps(
            {
                "event_id": f"event_{uuid.uuid4().hex}",
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(audio_chunk).decode("ascii"),
            }
        )
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                session = await self._get_session(session_id)
                await session.websocket.send(payload)
                return
            except (ConnectionClosed, OSError) as exc:
                last_error = exc
                current = self._sessions.pop(session_id, None)
                if current:
                    await self._dispose_session(current)
                if attempt == 0:
                    await asyncio.sleep(0.2)
                    continue
            except Exception as exc:
                last_error = exc
                break

        raise ConnectionError(
            f"Qwen audio connection failed after reconnect: {last_error}"
        )

    async def receive_result(self, session_id: str) -> ASRResult:
        while True:
            session = self._sessions.get(session_id)
            if session is None:
                await asyncio.sleep(0.05)
                continue

            result_task = asyncio.create_task(session.results.get())
            closed_task = asyncio.create_task(session.closed.wait())
            done, pending = await asyncio.wait(
                {result_task, closed_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

            if result_task in done:
                result = result_task.result()
                if not result.is_final and session.pending_partial is not None:
                    result = session.pending_partial
                    session.pending_partial = None
                return result

            if not session.results.empty():
                return session.results.get_nowait()

            if self._sessions.get(session_id) is session:
                await asyncio.sleep(0.05)

    async def finish_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session or session.finished:
            return
        session.finish_requested = True
        session.finish_confirmed.clear()
        await session.websocket.send(
            json.dumps(
                {
                    "event_id": f"event_{uuid.uuid4().hex}",
                    "type": "session.finish",
                }
            )
        )
        try:
            await asyncio.wait_for(
                session.finish_confirmed.wait(),
                timeout=self.finish_timeout_seconds,
            )
        except asyncio.TimeoutError:
            pass
        session.finished = True

    async def close_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        await self.finish_session(session_id)
        self._sessions.pop(session_id, None)
        await self._dispose_session(session)
