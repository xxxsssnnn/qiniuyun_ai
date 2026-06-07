import unittest
from unittest.mock import AsyncMock, patch

from app.services.asr import ASRResult, MockASRProvider
from app.services.streaming import TranscriptBuffer
from app.services.transcription_processor import TranscriptionProcessor
from app.services.translation import MockTranslationProvider


class TranscriptionProcessorTranslationTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_model_translation_is_not_overwritten_by_second_provider(
        self,
    ) -> None:
        manager = AsyncMock()
        translation_provider = MockTranslationProvider()
        translation_provider.translate = AsyncMock(
            side_effect=AssertionError("second translation must not run")
        )
        processor = TranscriptionProcessor(
            manager,
            TranscriptBuffer(),
            MockASRProvider(),
            translation_provider,
        )

        with patch(
            "app.services.transcription_processor.transcript_store.save_chunk"
        ):
            await processor.handle_asr_result(
                "session-1",
                ASRResult(
                    text="你好",
                    translated_text="Hello",
                    is_final=True,
                    confidence=1.0,
                    language="zh",
                ),
            )

        translation_provider.translate.assert_not_awaited()
        final_messages = [
            call.args[1]
            for call in manager.broadcast.await_args_list
            if call.args[1]["type"] == "revision"
        ]
        self.assertEqual(len(final_messages), 1)
        self.assertEqual(final_messages[0]["payload"]["sourceText"], "你好")
        self.assertEqual(final_messages[0]["payload"]["translatedText"], "Hello")


if __name__ == "__main__":
    unittest.main()
