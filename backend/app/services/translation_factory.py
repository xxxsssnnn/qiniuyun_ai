import os

from app.services.openai_translation import OpenAITranslationProvider
from app.services.translation import MockTranslationProvider, TranslationProvider


def get_translation_provider() -> TranslationProvider:
    provider_name = os.getenv("TRANSLATION_PROVIDER", "mock").lower()
    if provider_name == "openai":
        return OpenAITranslationProvider()
    return MockTranslationProvider()
