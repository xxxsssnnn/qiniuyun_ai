import os

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
    qwen_asr_model: str = 'qwen3-asr-flash-realtime'
    qwen_asr_language: str = 'en'
    dashscope_region: str = 'cn'


@router.get('')
async def get_settings(db: Session = Depends(get_db)) -> dict[str, str | bool]:
    stored = config_store.all(db)
    api_key_configured = bool(
        os.getenv('DASHSCOPE_API_KEY')
        or os.getenv('QWEN_API_KEY')
        or os.getenv('ALIYUN_API_KEY')
    )
    return {
        'asr_provider': stored.get('ASR_PROVIDER', 'mock'),
        'translation_provider': stored.get('TRANSLATION_PROVIDER', 'mock'),
        'tts_provider': stored.get('TTS_PROVIDER', 'mock'),
        'qwen_asr_model': stored.get('QWEN_ASR_MODEL', os.getenv('QWEN_ASR_MODEL', 'qwen3-asr-flash-realtime')),
        'qwen_asr_language': stored.get('QWEN_ASR_LANGUAGE', os.getenv('QWEN_ASR_LANGUAGE', 'en')),
        'dashscope_region': stored.get('DASHSCOPE_REGION', os.getenv('DASHSCOPE_REGION', 'cn')),
        'dashscope_api_key_configured': api_key_configured,
    }


@router.put('')
async def update_settings(payload: SettingsPayload, db: Session = Depends(get_db)) -> dict[str, str]:
    config_store.set(db, 'ASR_PROVIDER', payload.asr_provider)
    config_store.set(db, 'TRANSLATION_PROVIDER', payload.translation_provider)
    config_store.set(db, 'TTS_PROVIDER', payload.tts_provider)
    config_store.set(db, 'QWEN_ASR_MODEL', payload.qwen_asr_model)
    config_store.set(db, 'QWEN_ASR_LANGUAGE', payload.qwen_asr_language)
    config_store.set(db, 'DASHSCOPE_REGION', payload.dashscope_region)
    apply_runtime_setting('ASR_PROVIDER', payload.asr_provider)
    apply_runtime_setting('TRANSLATION_PROVIDER', payload.translation_provider)
    apply_runtime_setting('TTS_PROVIDER', payload.tts_provider)
    apply_runtime_setting('QWEN_ASR_MODEL', payload.qwen_asr_model)
    apply_runtime_setting('QWEN_ASR_LANGUAGE', payload.qwen_asr_language)
    apply_runtime_setting('DASHSCOPE_REGION', payload.dashscope_region)
    return {
        'asr_provider': payload.asr_provider,
        'translation_provider': payload.translation_provider,
        'tts_provider': payload.tts_provider,
        'qwen_asr_model': payload.qwen_asr_model,
        'qwen_asr_language': payload.qwen_asr_language,
        'dashscope_region': payload.dashscope_region,
    }


@router.post('/test-qwen')
async def test_qwen_connection() -> dict[str, str | bool]:
    from app.services.qwen_asr import QwenASRProvider

    provider = QwenASRProvider()
    if not provider.api_key:
        return {'ok': False, 'message': '未检测到 DASHSCOPE_API_KEY 环境变量'}
    try:
        await provider.test_connection()
        return {'ok': True, 'message': f'千问实时语音识别连接成功：{provider.model}'}
    except Exception as exc:
        return {'ok': False, 'message': f'千问连接失败：{exc}'}
