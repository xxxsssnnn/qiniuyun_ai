from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ASRResult:
    text: str
    translated_text: str | None = None
    is_final: bool = False
    confidence: float = 0.0
    language: str = "en"
    revision: int = 0


class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        raise NotImplementedError

    async def close_session(self, session_id: str) -> None:
        return None


class MockASRProvider(ASRProvider):
    def __init__(self) -> None:
        self._counter = 0

    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        self._counter += 1
        return ASRResult(
            text=f"[ASR] detected speech segment {self._counter}",
            is_final=self._counter % 3 == 0,
            confidence=0.72,
            language="en",
            revision=0,
        )
