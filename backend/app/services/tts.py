from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TTSResult:
    text: str
    audio_bytes: bytes = b''


class TTSProvider(ABC):
    @abstractmethod
    async def speak(self, text: str, language: str = 'zh') -> TTSResult:
        raise NotImplementedError


class MockTTSProvider(TTSProvider):
    async def speak(self, text: str, language: str = 'zh') -> TTSResult:
        return TTSResult(text=f"[{language}] {text}", audio_bytes=b'')
