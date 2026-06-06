import os

from app.services.openai_tts import OpenAITTSProvider
from app.services.tts import MockTTSProvider, TTSProvider


def get_tts_provider() -> TTSProvider:
    provider_name = os.getenv('TTS_PROVIDER', 'mock').lower()
    if provider_name == 'openai':
        return OpenAITTSProvider()
    return MockTTSProvider()
