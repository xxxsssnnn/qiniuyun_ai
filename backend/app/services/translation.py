from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional

from app.services.glossary import glossary_manager


@dataclass
class TranslationRequest:
    text: str
    source_language: str = "en"
    target_language: str = "zh"
    session_id: str = ""


@dataclass
class TranslationResult:
    source_text: str
    translated_text: str
    is_final: bool = False


class TranslationProvider(ABC):
    @abstractmethod
    async def translate(self, text: str, source_language: str = "en", target_language: str = "zh", session_id: str = "") -> TranslationResult:
        raise NotImplementedError


class TranslationService:
    def __init__(self, provider: Optional[TranslationProvider] = None) -> None:
        self.provider = provider or MockTranslationProvider()

    async def translate(self, request: TranslationRequest) -> TranslationResult:
        return await self.provider.translate(
            request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            session_id=request.session_id,
        )


class MockTranslationProvider(TranslationProvider):
    async def translate(self, text: str, source_language: str = "en", target_language: str = "zh", session_id: str = "") -> TranslationResult:
        normalized = glossary_manager.apply_glossary(text)
        context = glossary_manager.get_context(session_id) if session_id else []
        context_hint = f" | 上下文:{len(context)}段" if context else ""
        translated = f"【{target_language}】{normalized}{context_hint}"
        return TranslationResult(source_text=text, translated_text=translated, is_final=False)
