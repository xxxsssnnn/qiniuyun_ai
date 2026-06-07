import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.services.qwen_asr import QwenASRProvider, QwenRealtimeSession


class EventWebSocket:
    def __init__(self, events: list[dict]) -> None:
        self._events = iter(events)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            return json.dumps(next(self._events))
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class QwenASRProviderTestCase(unittest.TestCase):
    def test_long_sentence_pauses_use_semantic_vad_with_high_sensitivity(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            provider = QwenASRProvider()

        self.assertEqual(
            provider.turn_detection_config(),
            {
                "type": "semantic_vad",
                "threshold": 0.1,
                "prefix_padding_ms": 500,
                "silence_duration_ms": 900,
                "create_response": True,
                "interrupt_response": True,
            },
        )

    def test_vad_silence_duration_is_configurable_and_bounded(self) -> None:
        with patch.dict(os.environ, {"QWEN_VAD_SILENCE_MS": "1200"}):
            provider = QwenASRProvider()
        self.assertEqual(provider.vad_silence_duration_ms, 1200)

        with patch.dict(os.environ, {"QWEN_VAD_SILENCE_MS": "10000"}):
            provider = QwenASRProvider()
        self.assertEqual(provider.vad_silence_duration_ms, 3000)

        with patch.dict(os.environ, {"QWEN_VAD_SILENCE_MS": "invalid"}):
            provider = QwenASRProvider()
        self.assertEqual(provider.vad_silence_duration_ms, 900)

    def test_discontinuous_speech_vad_parameters_are_bounded(self) -> None:
        with patch.dict(
            os.environ,
            {
                "QWEN_VAD_THRESHOLD": "0.05",
                "QWEN_VAD_PREFIX_PADDING_MS": "5000",
                "QWEN_VAD_SILENCE_MS": "1200",
            },
        ):
            provider = QwenASRProvider()

        config = provider.turn_detection_config()
        self.assertEqual(config["threshold"], 0.1)
        self.assertEqual(config["prefix_padding_ms"], 1000)
        self.assertEqual(config["silence_duration_ms"], 1200)
        self.assertTrue(config["interrupt_response"])

    def test_models_without_semantic_vad_fall_back_to_server_vad(self) -> None:
        with patch.dict(
            os.environ,
            {
                "QWEN_ASR_MODEL": "qwen3-omni-flash-realtime",
                "QWEN_VAD_TYPE": "semantic_vad",
            },
        ):
            provider = QwenASRProvider()

        self.assertEqual(provider.turn_detection_config()["type"], "server_vad")


class QwenASRFinishTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_finish_waits_for_server_session_confirmation(self) -> None:
        provider = QwenASRProvider()
        provider.finish_timeout_seconds = 0.2
        websocket = AsyncMock()
        session = QwenRealtimeSession(websocket=websocket, language="en")
        provider._sessions["session-1"] = session

        async def confirm_finish(_: str) -> None:
            session.finish_confirmed.set()

        websocket.send.side_effect = confirm_finish
        await provider.finish_session("session-1")

        sent_payload = websocket.send.await_args.args[0]
        self.assertIn('"type": "session.finish"', sent_payload)
        self.assertTrue(session.finished)


class QwenASRMultiTurnTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_second_sentence_survives_while_first_response_finishes(
        self,
    ) -> None:
        provider = QwenASRProvider()
        websocket = EventWebSocket(
            [
                {
                    "type": "conversation.item.input_audio_transcription.completed",
                    "transcript": "First sentence.",
                },
                {"type": "response.created"},
                {
                    "type": "conversation.item.input_audio_transcription.completed",
                    "transcript": "Second sentence.",
                },
                {
                    "type": "response.text.done",
                    "text": "第一句话。",
                },
                {"type": "response.done"},
                {"type": "response.created"},
                {
                    "type": "response.text.done",
                    "text": "第二句话。",
                },
                {"type": "response.done"},
            ]
        )
        session = QwenRealtimeSession(websocket=websocket, language="en")

        await provider._read_events(session)

        first = session.results.get_nowait()
        second = session.results.get_nowait()
        self.assertEqual(
            (first.text, first.translated_text),
            ("First sentence.", "第一句话。"),
        )
        self.assertEqual(
            (second.text, second.translated_text),
            ("Second sentence.", "第二句话。"),
        )
        self.assertTrue(session.results.empty())


if __name__ == "__main__":
    unittest.main()
