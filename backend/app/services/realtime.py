from dataclasses import dataclass
from typing import Optional

from app.services.streaming import TranscriptBuffer, TranscriptChunk


@dataclass
class RealtimeTranscriptState:
    buffer: TranscriptBuffer

    def append(self, chunk: TranscriptChunk) -> None:
        self.buffer.append(chunk)

    def latest(self) -> Optional[TranscriptChunk]:
        return self.buffer.latest()
