from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional


@dataclass
class TranscriptChunk:
    chunk_id: str
    source_text: str
    translated_text: str = ""
    direct_translation: str = ""
    is_final: bool = False
    session_id: str = "default"
    revision: int = 0
    auto_correction: bool = False
    correction_reasons: list[str] = field(default_factory=list)


@dataclass
class TranscriptBuffer:
    max_items: int = 200
    items: Deque[TranscriptChunk] = field(default_factory=deque)

    def append(self, chunk: TranscriptChunk) -> None:
        self.items.append(chunk)
        while len(self.items) > self.max_items:
            self.items.popleft()

    def upsert(self, chunk: TranscriptChunk) -> None:
        for index, item in enumerate(self.items):
            if item.chunk_id == chunk.chunk_id:
                self.items[index] = chunk
                return
        self.append(chunk)

    def latest(self, session_id: str | None = None) -> Optional[TranscriptChunk]:
        if session_id is None:
            return self.items[-1] if self.items else None
        for item in reversed(self.items):
            if item.session_id == session_id:
                return item
        return None

    def list_session(self, session_id: str, final_only: bool = False) -> list[TranscriptChunk]:
        chunks = [item for item in self.items if item.session_id == session_id]
        if final_only:
            chunks = [item for item in chunks if item.is_final]
        return chunks

    def export_session(self, session_id: str, fmt: str = "json") -> str | list[dict]:
        chunks = self.list_session(session_id, final_only=True)
        if fmt == "srt":
            return self._to_srt(chunks)
        if fmt == "txt":
            return "\n".join(
                f"{index + 1}. {chunk.source_text}\n{chunk.translated_text}"
                for index, chunk in enumerate(chunks)
            )
        return [
            {
                "chunk_id": chunk.chunk_id,
                "session_id": chunk.session_id,
                "source_text": chunk.source_text,
                "translated_text": chunk.translated_text,
                "direct_translation": chunk.direct_translation,
                "is_final": chunk.is_final,
                "revision": chunk.revision,
                "auto_correction": chunk.auto_correction,
                "correction_reasons": chunk.correction_reasons,
            }
            for chunk in chunks
        ]

    def _to_srt(self, chunks: list[TranscriptChunk]) -> str:
        blocks: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            start_seconds = max(0, index - 1) * 4
            end_seconds = start_seconds + 4
            blocks.append(
                "\n".join(
                    [
                        str(index),
                        f"{self._format_srt_time(start_seconds)} --> {self._format_srt_time(end_seconds)}",
                        chunk.source_text,
                        chunk.translated_text,
                    ]
                )
            )
        return "\n\n".join(blocks)

    def _format_srt_time(self, total_seconds: int) -> str:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02},000"
