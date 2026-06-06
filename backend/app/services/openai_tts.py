from __future__ import annotations

import os
from typing import Any

from app.services.tts import MockTTSProvider, TTSProvider, TTSResult


class OpenAITTSProvider(TTSProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = os.getenv('OPENAI_TTS_MODEL', 'gpt-4o-mini-tts')
        self.voice = os.getenv('OPENAI_TTS_VOICE', 'alloy')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self._fallback = MockTTSProvider()
        self._client: Any = None
        try:
            from openai import OpenAI  # type: ignore

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception:
            self._client = None

    async def speak(self, text: str, language: str = 'zh') -> TTSResult:
        if not self.api_key or self._client is None:
            return await self._fallback.speak(text, language=language)

        try:
            response = self._client.audio.speech.create(
                model=self.model,
                voice=self.voice,
                input=text,
                format='mp3',
            )
            audio_bytes = getattr(response, 'content', b'') or b''
            return TTSResult(text=f'[{language}] {text}', audio_bytes=audio_bytes)
        except Exception:
            return await self._fallback.speak(text, language=language)
