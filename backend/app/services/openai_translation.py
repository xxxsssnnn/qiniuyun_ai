from __future__ import annotations

import os
from typing import Any

from app.services.translation import TranslationProvider, TranslationResult


class OpenAITranslationProvider(TranslationProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_TRANSLATION_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self._client: Any = None
        try:
            from openai import OpenAI  # type: ignore

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception:
            self._client = None

    async def translate(self, text: str, source_language: str = "en", target_language: str = "zh", session_id: str = "") -> TranslationResult:
        if not self.api_key or self._client is None:
            return TranslationResult(source_text=text, translated_text=f"[OpenAI unavailable] {text}", is_final=False)

        prompt = (
            f"请把下面{source_language}内容翻译成{target_language}，保持术语统一，适合字幕阅读，输出自然、简洁、准确的中文。\n\n"
            f"原文：{text}"
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional simultaneous interpretation engine."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content if response.choices else None
            translated = (content or f"[OpenAI empty] {text}").strip()
            return TranslationResult(source_text=text, translated_text=translated, is_final=True)
        except Exception:
            return TranslationResult(source_text=text, translated_text=f"[OpenAI error] {text}", is_final=False)
