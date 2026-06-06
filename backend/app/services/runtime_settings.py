import os

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.config_store import config_store


SETTING_KEYS = {
    'ASR_PROVIDER': 'ASR_PROVIDER',
    'TRANSLATION_PROVIDER': 'TRANSLATION_PROVIDER',
    'TTS_PROVIDER': 'TTS_PROVIDER',
}


def load_runtime_settings() -> dict[str, str]:
    db: Session = SessionLocal()
    try:
        stored = config_store.all(db)
        for key, value in stored.items():
            os.environ[key] = value
        return stored
    finally:
        db.close()


def apply_runtime_setting(key: str, value: str) -> str:
    os.environ[key] = value
    return value
