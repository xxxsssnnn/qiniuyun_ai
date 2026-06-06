from __future__ import annotations

import os

from app.services.tts import MockTTSProvider, TTSProvider, TTSResult


class OpenAITTSProvider(TTSProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.model = os.getenv('OPENAI_TTS_MODEL', 'gpt-4o-mini-tts')
        self.voice = os.getenv('OPENAI_TTS_VOICE', 'alloy')
        self._fallback = MockTTSProvider()

    async def speak(self, text: str, language: str = 'zh') -> TTSResult:
        if not self.api_key:
            return await self._fallback.speak(text, language=language)

        # Placeholder for real TTS API integration.
        # Replace with actual HTTP call to your TTS provider when credentials are configured.
        return TTSResult(text=f'[{language}] {text}', audio_bytes=b'')
