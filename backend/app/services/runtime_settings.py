import os

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.config_store import config_store


SETTING_KEYS = {
    'ASR_PROVIDER': 'ASR_PROVIDER',
    'TRANSLATION_PROVIDER': 'TRANSLATION_PROVIDER',
    'TTS_PROVIDER': 'TTS_PROVIDER',
    'OPENAI_API_KEY': 'OPENAI_API_KEY',
    'OPENAI_BASE_URL': 'OPENAI_BASE_URL',
    'OPENAI_MODEL': 'OPENAI_MODEL',
    'OPENAI_TRANSLATION_MODEL': 'OPENAI_TRANSLATION_MODEL',
    'OPENAI_TTS_MODEL': 'OPENAI_TTS_MODEL',
    'OPENAI_TTS_VOICE': 'OPENAI_TTS_VOICE',
    'WHISPER_MODEL': 'WHISPER_MODEL',
    'WHISPER_DEVICE': 'WHISPER_DEVICE',
    'WHISPER_COMPUTE_TYPE': 'WHISPER_COMPUTE_TYPE',
    'DEEPSEEK_API_KEY': 'DEEPSEEK_API_KEY',
    'DEEPSEEK_BASE_URL': 'DEEPSEEK_BASE_URL',
    'DEEPSEEK_MODEL': 'DEEPSEEK_MODEL',
}


def load_runtime_settings() -> dict[str, str]:
    db: Session = SessionLocal()
    try:
        return apply_runtime_settings(db)
    finally:
        db.close()


def apply_runtime_settings(session: Session) -> dict[str, str]:
    stored = config_store.all(session)
    for key, value in stored.items():
        os.environ[key] = value
    return stored


def apply_runtime_setting(key: str, value: str) -> str:
    os.environ[key] = value
    return value
