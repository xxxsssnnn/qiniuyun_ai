from __future__ import annotations

import os
from typing import Any

from app.services.glossary import glossary_manager
from app.services.translation import TranslationProvider, TranslationResult


class DeepSeekTranslationProvider(TranslationProvider):
    def __init__(self) -> None:
        self.api_key = os.getenv('DEEPSEEK_API_KEY', '')
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        self.base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
        self._client: Any = None
        try:
            from openai import OpenAI  # type: ignore

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        except Exception:
            self._client = None

    async def translate(self, text: str, source_language: str = 'en', target_language: str = 'zh', session_id: str = '') -> TranslationResult:
        if not self.api_key or self._client is None:
            normalized = glossary_manager.apply_glossary(text)
            return TranslationResult(source_text=text, translated_text=f'[DeepSeek unavailable] {normalized}', is_final=False)

        context = glossary_manager.get_context(session_id) if session_id else []
        context_text = '\n'.join(context[-6:]) if context else '无额外上下文'
        glossary_hint = glossary_manager.format_prompt(text) or '无术语表'
        prompt = (
            f'请将下面{source_language}内容翻译成{target_language}，要求：\n'
            f'1. 适合字幕阅读，尽量简洁自然\n'
            f'2. 保持术语统一\n'
            f'3. 保留专有名词和上下文一致性\n\n'
            f'【术语表】\n{glossary_hint}\n\n'
            f'【上下文】\n{context_text}\n\n'
            f'【原文】\n{text}'
        )

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You are a professional simultaneous interpretation engine.'},
                    {'role': 'user', 'content': prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content if response.choices else None
            translated = (content or f'[DeepSeek empty] {text}').strip()
            return TranslationResult(source_text=text, translated_text=translated, is_final=True)
        except Exception:
            normalized = glossary_manager.apply_glossary(text)
            return TranslationResult(source_text=text, translated_text=f'[DeepSeek error] {normalized}', is_final=False)
