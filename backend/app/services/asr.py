from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class ASRResult:
    text: str
    is_final: bool = False
    confidence: float = 0.0


class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        raise NotImplementedError


class MockASRProvider(ASRProvider):
    def __init__(self) -> None:
        self._counter = 0

    async def transcribe(self, audio_chunk: bytes, session_id: str) -> ASRResult:
        self._counter += 1
        return ASRResult(
            text=f"[ASR] detected speech segment {self._counter}",
            is_final=self._counter % 3 == 0,
            confidence=0.72,
        )
