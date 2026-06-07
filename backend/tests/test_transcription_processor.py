import unittest
from unittest.mock import AsyncMock, PropertyMock, patch

from app.services.asr import ASRResult, MockASRProvider
from app.services.qwen_correction import QwenCorrection
from app.services.streaming import TranscriptBuffer, TranscriptChunk
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

    async def test_reconnected_session_generates_unique_chunk_ids(self) -> None:
        first_manager = AsyncMock()
        second_manager = AsyncMock()
        first_processor = TranscriptionProcessor(
            first_manager,
            TranscriptBuffer(),
            MockASRProvider(),
            MockTranslationProvider(),
        )
        second_processor = TranscriptionProcessor(
            second_manager,
            TranscriptBuffer(),
            MockASRProvider(),
            MockTranslationProvider(),
        )
        result = ASRResult(
            text="你好",
            translated_text="Hello",
            is_final=True,
            confidence=1.0,
            language="zh",
        )

        with patch(
            "app.services.transcription_processor.transcript_store.save_chunk"
        ):
            await first_processor.handle_asr_result("session-1", result)
            await second_processor.handle_asr_result("session-1", result)

        first_chunk_id = next(
            call.args[1]["payload"]["chunk_id"]
            for call in first_manager.broadcast.await_args_list
            if call.args[1]["type"] == "revision"
        )
        second_chunk_id = next(
            call.args[1]["payload"]["chunk_id"]
            for call in second_manager.broadcast.await_args_list
            if call.args[1]["type"] == "revision"
        )
        self.assertNotEqual(first_chunk_id, second_chunk_id)

    async def test_qwen_context_review_revises_previous_subtitle(self) -> None:
        manager = AsyncMock()
        buffer = TranscriptBuffer()
        buffer.append(
            TranscriptChunk(
                chunk_id="chunk-1",
                session_id="session-1",
                source_text="We use cash.",
                translated_text="我们使用现金。",
                is_final=True,
                revision=1,
            )
        )
        buffer.append(
            TranscriptChunk(
                chunk_id="chunk-2",
                session_id="session-1",
                source_text="The cache expires after one minute.",
                translated_text="缓存会在一分钟后过期。",
                is_final=True,
                revision=1,
            )
        )
        processor = TranscriptionProcessor(
            manager,
            buffer,
            MockASRProvider(),
            MockTranslationProvider(),
        )

        with (
            patch(
                "app.services.qwen_correction.QwenSubtitleCorrectionService.available",
                new_callable=PropertyMock,
                return_value=True,
            ),
            patch(
                "app.services.transcription_processor.qwen_correction_service.review",
                new=AsyncMock(
                    return_value=[
                        QwenCorrection(
                            chunk_id="chunk-1",
                            source_text="We use cache.",
                            translated_text="我们使用缓存。",
                            reason="后文表明这里指缓存而非现金",
                        )
                    ]
                ),
            ),
            patch(
                "app.services.transcription_processor.transcript_store.save_chunk"
            ) as save_chunk,
        ):
            await processor._review_context("session-1")

        corrected = buffer.list_session("session-1")[0]
        self.assertEqual(corrected.source_text, "We use cache.")
        self.assertEqual(corrected.translated_text, "我们使用缓存。")
        self.assertEqual(corrected.revision, 2)
        self.assertTrue(corrected.auto_correction)
        save_chunk.assert_called_once()
        correction_messages = [
            call.args[1]
            for call in manager.broadcast.await_args_list
            if call.args[1]["type"] == "correction"
        ]
        self.assertEqual(len(correction_messages), 1)
        self.assertEqual(
            correction_messages[0]["payload"]["chunk_id"],
            "chunk-1",
        )


if __name__ == "__main__":
    unittest.main()
