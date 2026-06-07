import os
import unittest
from unittest.mock import AsyncMock, patch

from app.services.qwen_asr import QwenASRProvider, QwenRealtimeSession


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


if __name__ == "__main__":
    unittest.main()
