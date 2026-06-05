from dataclasses import dataclass, field
from typing import Deque, Optional
from collections import deque


@dataclass
class TranscriptChunk:
    chunk_id: str
    source_text: str
    translated_text: str = ""
    is_final: bool = False


@dataclass
class TranscriptBuffer:
    max_items: int = 200
    items: Deque[TranscriptChunk] = field(default_factory=deque)

    def append(self, chunk: TranscriptChunk) -> None:
        self.items.append(chunk)
        while len(self.items) > self.max_items:
            self.items.popleft()

    def latest(self) -> Optional[TranscriptChunk]:
        return self.items[-1] if self.items else None
