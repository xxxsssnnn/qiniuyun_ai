from __future__ import annotations

import os
from typing import Any

from app.services.glossary import glossary_manager
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

        glossary_entries = glossary_manager.list_entries()
        glossary_text = "\n".join(
            f"- {entry.source} => {entry.target}{f'（{entry.note}）' if entry.note else ''}"
            for entry in glossary_entries[:30]
        ) or "无"
        context_items = glossary_manager.get_context(session_id)[-6:] if session_id else []
        context_text = "\n".join(f"- {item}" for item in context_items) or "无"

        prompt = (
            f"请把当前片段从{source_language}翻译成{target_language}。\n"
            "要求：\n"
            "1. 只输出译文，不解释，不添加标题。\n"
            "2. 适合实时字幕阅读，短句优先，自然准确。\n"
            "3. 保留人名、产品名、代码、API、数字和单位。\n"
            "4. 严格遵守术语表；上下文只用于消歧，不要重复翻译上下文。\n\n"
            f"术语表：\n{glossary_text}\n\n"
            f"最近上下文：\n{context_text}\n\n"
            f"当前片段：{text}"
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
