import os

from app.services.asr import ASRProvider, MockASRProvider


def get_asr_provider() -> ASRProvider:
    provider_name = os.getenv("ASR_PROVIDER", "mock").lower()
    if provider_name == "whisper":
        try:
            from app.services.whisper_asr import WhisperASRProvider

            return WhisperASRProvider()
        except Exception:
            return MockASRProvider()
    return MockASRProvider()
