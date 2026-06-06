from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.services.streaming import TranscriptChunk


@dataclass
class RevisionRecord:
    chunk_id: str
    source_text: str
    translated_text: str
    revision: int
    is_final: bool


class RevisionManager:
    def __init__(self) -> None:
        self._history: Dict[str, List[RevisionRecord]] = {}

    def record(self, chunk: TranscriptChunk, revision: int) -> RevisionRecord:
        record = RevisionRecord(
            chunk_id=chunk.chunk_id,
            source_text=chunk.source_text,
            translated_text=chunk.translated_text,
            revision=revision,
            is_final=chunk.is_final,
        )
        self._history.setdefault(chunk.chunk_id, []).append(record)
        return record

    def latest(self, chunk_id: str) -> Optional[RevisionRecord]:
        history = self._history.get(chunk_id)
        if not history:
            return None
        return history[-1]

    def all_versions(self, chunk_id: str) -> list[RevisionRecord]:
        return list(self._history.get(chunk_id, []))

    def rollback(self, chunk_id: str, revision: int) -> Optional[RevisionRecord]:
        history = self._history.get(chunk_id)
        if not history:
            return None
        for item in reversed(history):
            if item.revision <= revision:
                return item
        return history[0]


revision_manager = RevisionManager()
