import unittest

from app.services.qwen_correction import QwenSubtitleCorrectionService


class QwenSubtitleCorrectionServiceTestCase(unittest.TestCase):
    def test_json_code_fence_is_supported(self) -> None:
        service = QwenSubtitleCorrectionService()

        parsed = service._parse_json(
            '```json\n{"corrections": []}\n```'
        )

        self.assertEqual(parsed, {"corrections": []})


if __name__ == "__main__":
    unittest.main()
