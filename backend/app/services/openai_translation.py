from app.services.translation import TranslationProvider, TranslationResult


class OpenAITranslationProvider(TranslationProvider):
    def __init__(self) -> None:
        self._available = False
        self._client = None
        try:
            from openai import AsyncOpenAI  # type: ignore

            self._client = AsyncOpenAI()
            self._available = True
        except Exception:
            self._client = None

    async def translate(self, text: str, source_language: str = "en", target_language: str = "zh") -> TranslationResult:
        if not self._available or self._client is None:
            return TranslationResult(source_text=text, translated_text=f"[Translation unavailable] {text}", is_final=False)

        prompt = (
            f"Please translate the following {source_language} text into natural {target_language} Chinese for live subtitles. "
            f"Keep it concise and fluent. Text: {text}"
        )
        try:
            response = await self._client.responses.create(
                model="gpt-4.1-mini",
                input=prompt,
            )
            translated_text = response.output_text.strip() if hasattr(response, "output_text") else f"[OpenAI] {text}"
            return TranslationResult(source_text=text, translated_text=translated_text, is_final=True)
        except Exception:
            return TranslationResult(source_text=text, translated_text=f"[Translation error] {text}", is_final=False)
