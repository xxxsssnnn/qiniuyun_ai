from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.config_store import config_store
from app.services.runtime_settings import apply_runtime_settings

router = APIRouter()


class SettingsPayload(BaseModel):
    asr_provider: str = 'mock'
    translation_provider: str = 'mock'
    tts_provider: str = 'mock'
    openai_api_key: str = ''
    openai_base_url: str = 'https://api.openai.com/v1'
    openai_model: str = 'gpt-4o-mini'
    openai_translation_model: str = 'gpt-4o-mini'
    openai_tts_model: str = 'gpt-4o-mini-tts'
    openai_tts_voice: str = 'alloy'
    whisper_model: str = 'base'
    whisper_device: str = 'cpu'
    whisper_compute_type: str = 'int8'


@router.get('')
async def get_settings(db: Session = Depends(get_db)) -> dict[str, str]:
    return config_store.all(db)


@router.put('')
async def update_settings(payload: SettingsPayload, db: Session = Depends(get_db)) -> dict[str, str]:
    config_store.set(db, 'ASR_PROVIDER', payload.asr_provider)
    config_store.set(db, 'TRANSLATION_PROVIDER', payload.translation_provider)
    config_store.set(db, 'TTS_PROVIDER', payload.tts_provider)
    config_store.set(db, 'OPENAI_API_KEY', payload.openai_api_key)
    config_store.set(db, 'OPENAI_BASE_URL', payload.openai_base_url)
    config_store.set(db, 'OPENAI_MODEL', payload.openai_model)
    config_store.set(db, 'OPENAI_TRANSLATION_MODEL', payload.openai_translation_model)
    config_store.set(db, 'OPENAI_TTS_MODEL', payload.openai_tts_model)
    config_store.set(db, 'OPENAI_TTS_VOICE', payload.openai_tts_voice)
    config_store.set(db, 'WHISPER_MODEL', payload.whisper_model)
    config_store.set(db, 'WHISPER_DEVICE', payload.whisper_device)
    config_store.set(db, 'WHISPER_COMPUTE_TYPE', payload.whisper_compute_type)
    apply_runtime_settings(db)
    return {
        'asr_provider': payload.asr_provider,
        'translation_provider': payload.translation_provider,
        'tts_provider': payload.tts_provider,
        'openai_api_key': payload.openai_api_key,
        'openai_base_url': payload.openai_base_url,
        'openai_model': payload.openai_model,
        'openai_translation_model': payload.openai_translation_model,
        'openai_tts_model': payload.openai_tts_model,
        'openai_tts_voice': payload.openai_tts_voice,
        'whisper_model': payload.whisper_model,
        'whisper_device': payload.whisper_device,
        'whisper_compute_type': payload.whisper_compute_type,
    }
