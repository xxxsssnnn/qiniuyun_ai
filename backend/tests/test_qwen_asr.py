import asyncio
import base64
import json
import unittest

from app.services.asr import ASRResult
from app.services.qwen_asr import (
    REALTIME_VAD_CONFIG,
    QwenASRProvider,
    QwenRealtimeSession,
)
from app.services.streaming import TranscriptBuffer
from app.services.transcription_processor import TranscriptionProcessor


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[str] = []

    async def send(self, message: str) -> None:
        self.messages.append(message)


class FakeManager:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def broadcast(self, _session_id: str, message: dict) -> None:
        self.messages.append(message)


class FailingTranslationProvider:
    async def translate(self, *_args, **_kwargs):
        raise AssertionError("ASR errors must not be translated")


class QwenASRProviderTest(unittest.IsolatedAsyncioTestCase):
    async def test_vad_config_preserves_natural_speech_pauses(self) -> None:
        self.assertEqual(REALTIME_VAD_CONFIG["threshold"], 0.0)
        self.assertEqual(REALTIME_VAD_CONFIG["prefix_padding_ms"], 500)
        self.assertEqual(REALTIME_VAD_CONFIG["silence_duration_ms"], 900)
        self.assertFalse(REALTIME_VAD_CONFIG["interrupt_response"])

    async def test_finish_session_flushes_with_silence(self) -> None:
        provider = QwenASRProvider()
        websocket = FakeWebSocket()
        session = QwenRealtimeSession(websocket=websocket, language="en")
        provider._sessions["test-session"] = session

        finish_task = asyncio.create_task(
            provider.finish_session("test-session")
        )
        await asyncio.sleep(0)
        session.response_done.set()
        await finish_task

        self.assertTrue(session.finished)
        self.assertEqual(len(websocket.messages), 1)
        payload = json.loads(websocket.messages[0])
        self.assertEqual(payload["type"], "input_audio_buffer.append")
        self.assertEqual(len(base64.b64decode(payload["audio"])), 16000)

    async def test_finish_session_never_sends_unsupported_event(self) -> None:
        provider = QwenASRProvider()
        websocket = FakeWebSocket()
        session = QwenRealtimeSession(websocket=websocket, language="en")
        provider._sessions["test-session"] = session

        finish_task = asyncio.create_task(
            provider.finish_session("test-session")
        )
        await asyncio.sleep(0)
        session.response_done.set()
        await finish_task

        event_types = [
            json.loads(message)["type"] for message in websocket.messages
        ]
        self.assertNotIn("session.finish", event_types)

    async def test_asr_error_is_not_published_as_subtitle(self) -> None:
        manager = FakeManager()
        processor = TranscriptionProcessor(
            manager,
            TranscriptBuffer(),
            QwenASRProvider(),
            FailingTranslationProvider(),
        )

        await processor.handle_asr_result(
            "test-session",
            ASRResult(text="", error="Qwen ASR error: invalid event"),
        )

        self.assertEqual(len(manager.messages), 1)
        self.assertEqual(manager.messages[0]["type"], "error")


if __name__ == "__main__":
    unittest.main()
