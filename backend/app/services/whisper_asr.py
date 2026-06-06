from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.asr import ASRProvider, ASRResult


class WhisperASRProvider(ASRProvider):
    def __init__(self, model_name: str = "base") -> None:
        self.model_name = model_name
        self._available = False
        self._model = None
        try:
            import whisper  # type: ignore

            self._whisper = whisper
            self._model = whisper.load_model(model_name)
            self._available = True
        except Exception:
            self._whisper = None
            self._model = None

    def _write_temp_audio(self, audio_chunk: bytes) -> Path:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        temp_path = Path(temp_file.name)
        temp_file.write(audio_chunk)
        temp_file.close()
        return temp_path

    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        if not self._available or self._model is None:
            return ASRResult(
                text="[Whisper unavailable] fallback mock transcript",
                is_final=False,
                confidence=0.0,
                language="en",
                revision=0,
            )

        temp_path = self._write_temp_audio(audio_chunk)
        try:
            result = self._model.transcribe(str(temp_path), language="en", fp16=False)
            text = result.get("text", "").strip() or "[Whisper] empty transcription"
            return ASRResult(
                text=text,
                is_final=True,
                confidence=0.85,
                language="en",
                revision=0,
            )
        except Exception:
            return ASRResult(
                text="[Whisper error] fallback mock transcript",
                is_final=False,
                confidence=0.0,
                language="en",
                revision=0,
            )
        finally:
            try:
                temp_path.unlink(missing_ok=True)
            except Exception:
                pass
