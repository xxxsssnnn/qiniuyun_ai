import unittest

from app.services.asr import ASRResult, MockASRProvider
from app.services.streaming import TranscriptBuffer
from app.services.transcription_processor import TranscriptionProcessor


class FakeManager:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def broadcast(self, _session_id: str, message: dict) -> None:
        self.messages.append(message)


class UnusedTranslationProvider:
    async def translate(self, *_args, **_kwargs):
        raise AssertionError("pre-translated ASR results should not be translated")


class TranscriptionProcessorTest(unittest.IsolatedAsyncioTestCase):
    def create_processor(self) -> tuple[TranscriptionProcessor, FakeManager]:
        manager = FakeManager()
        processor = TranscriptionProcessor(
            manager,
            TranscriptBuffer(),
            MockASRProvider(),
            UnusedTranslationProvider(),
        )
        return processor, manager

    async def test_merges_adjacent_incomplete_segments(self) -> None:
        processor, manager = self.create_processor()

        await processor.handle_asr_result(
            "session",
            ASRResult(
                text="Today we are going to discuss",
                translated_text="今天我们将讨论",
                is_final=True,
            ),
        )
        await processor.handle_asr_result(
            "session",
            ASRResult(
                text="realtime translation.",
                translated_text="实时翻译。",
                is_final=True,
            ),
        )

        first = manager.messages[0]["payload"]
        second = manager.messages[1]["payload"]
        self.assertEqual(second["chunk_id"], first["chunk_id"])
        self.assertEqual(
            second["sourceText"],
            "Today we are going to discuss realtime translation.",
        )
        self.assertEqual(second["translatedText"], "今天我们将讨论实时翻译。")

    async def test_keeps_complete_sentences_separate(self) -> None:
        processor, manager = self.create_processor()

        await processor.handle_asr_result(
            "session",
            ASRResult(
                text="The first sentence is complete.",
                translated_text="第一句话已经完整。",
                is_final=True,
            ),
        )
        await processor.handle_asr_result(
            "session",
            ASRResult(
                text="This is another sentence.",
                translated_text="这是另一句话。",
                is_final=True,
            ),
        )

        first = manager.messages[0]["payload"]
        second = manager.messages[1]["payload"]
        self.assertNotEqual(second["chunk_id"], first["chunk_id"])
        self.assertEqual(second["sourceText"], "This is another sentence.")


if __name__ == "__main__":
    unittest.main()
