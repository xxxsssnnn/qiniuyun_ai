from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class TranslationResult:
    source_text: str
    translated_text: str
    is_final: bool = False


class TranslationProvider(ABC):
    @abstractmethod
    async def translate(self, text: str, source_language: str = "en", target_language: str = "zh") -> TranslationResult:
        raise NotImplementedError


class MockTranslationProvider(TranslationProvider):
    async def translate(self, text: str, source_language: str = "en", target_language: str = "zh") -> TranslationResult:
        translated = f"【{target_language}】{text}"
        return TranslationResult(source_text=text, translated_text=translated, is_final=False)
