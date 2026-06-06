from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.config_store import config_store
from app.services.runtime_settings import apply_runtime_setting

router = APIRouter()


class SettingsPayload(BaseModel):
    asr_provider: str = 'mock'
    translation_provider: str = 'mock'
    tts_provider: str = 'mock'


@router.get('')
async def get_settings(db: Session = Depends(get_db)) -> dict[str, str]:
    stored = config_store.all(db)
    return {
        'asr_provider': stored.get('ASR_PROVIDER', 'mock'),
        'translation_provider': stored.get('TRANSLATION_PROVIDER', 'mock'),
        'tts_provider': stored.get('TTS_PROVIDER', 'mock'),
    }


@router.put('')
async def update_settings(payload: SettingsPayload, db: Session = Depends(get_db)) -> dict[str, str]:
    config_store.set(db, 'ASR_PROVIDER', payload.asr_provider)
    config_store.set(db, 'TRANSLATION_PROVIDER', payload.translation_provider)
    config_store.set(db, 'TTS_PROVIDER', payload.tts_provider)
    apply_runtime_setting('ASR_PROVIDER', payload.asr_provider)
    apply_runtime_setting('TRANSLATION_PROVIDER', payload.translation_provider)
    apply_runtime_setting('TTS_PROVIDER', payload.tts_provider)
    return {
        'asr_provider': payload.asr_provider,
        'translation_provider': payload.translation_provider,
        'tts_provider': payload.tts_provider,
    }
