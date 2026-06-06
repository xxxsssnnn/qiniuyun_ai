from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from app.services.asr import ASRProvider, ASRResult


class WhisperASRProvider(ASRProvider):
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or os.getenv("WHISPER_MODEL", "base")
        self._backend = "mock"
        self._model: Any = None
        self._backend_name = "unavailable"

        try:
            import whisper  # type: ignore

            self._model = whisper.load_model(self.model_name)
            self._backend = "openai-whisper"
            self._backend_name = self.model_name
            return
        except Exception:
            self._model = None

        try:
            from faster_whisper import WhisperModel  # type: ignore

            device = os.getenv("WHISPER_DEVICE", "cpu")
            compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
            self._model = WhisperModel(self.model_name, device=device, compute_type=compute_type)
            self._backend = "faster-whisper"
            self._backend_name = f"{self.model_name}:{device}:{compute_type}"
            return
        except Exception:
            self._model = None

    @property
    def available(self) -> bool:
        return self._model is not None

    @property
    def backend(self) -> str:
        return self._backend

    def _write_temp_audio(self, audio_chunk: bytes) -> Path:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        temp_path = Path(temp_file.name)
        temp_file.write(audio_chunk)
        temp_file.close()
        return temp_path

    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        if not self.available or self._model is None:
            return ASRResult(
                text="[Whisper unavailable] fallback mock transcript",
                is_final=False,
                confidence=0.0,
                language="en",
                revision=0,
            )

        temp_path = self._write_temp_audio(audio_chunk)
        try:
            if self._backend == "openai-whisper":
                result = self._model.transcribe(str(temp_path), language="en", fp16=False)
                text = result.get("text", "").strip() if isinstance(result, dict) else ""
                text = text or "[Whisper] empty transcription"
                confidence = 0.85 if text and not text.startswith("[") else 0.6
                return ASRResult(text=text, is_final=True, confidence=confidence, language="en", revision=0)

            segments, info = self._model.transcribe(str(temp_path), language="en")
            text = " ".join((segment.text or "").strip() for segment in segments).strip()
            text = text or "[Whisper] empty transcription"
            confidence = float(getattr(info, "probability", 0.75) or 0.75)
            return ASRResult(text=text, is_final=True, confidence=confidence, language="en", revision=0)
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
