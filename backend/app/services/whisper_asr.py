from app.services.asr import ASRProvider, ASRResult


class WhisperASRProvider(ASRProvider):
    def __init__(self) -> None:
        self._available = False
        try:
            import whisper  # type: ignore

            self._whisper = whisper
            self._available = True
        except Exception:
            self._whisper = None

    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        if not self._available:
            return ASRResult(
                text="[Whisper unavailable] fallback mock transcript",
                is_final=False,
                confidence=0.0,
                language="en",
                revision=0,
            )

        # 这里先保留真实接口位置，后续可接入音频解码和模型推理
        return ASRResult(
            text="[Whisper] real transcription placeholder",
            is_final=False,
            confidence=0.8,
            language="en",
            revision=0,
        )
