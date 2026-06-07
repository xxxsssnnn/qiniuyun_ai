from dataclasses import dataclass
from typing import Dict, List, Optional

from app.services.streaming import TranscriptChunk


@dataclass
class RevisionRecord:
    chunk_id: str
    source_text: str
    translated_text: str
    direct_translation: str
    revision: int
    is_final: bool


@dataclass
class CorrectionEvent:
    chunk_id: str
    previous_revision: int
    current_revision: int
    source_text: str
    translated_text: str
    direct_translation: str
    is_final: bool


class RevisionManager:
    def __init__(self) -> None:
        self._history: Dict[str, List[RevisionRecord]] = {}

    def record(self, chunk: TranscriptChunk, revision: int) -> RevisionRecord:
        record = RevisionRecord(
            chunk_id=chunk.chunk_id,
            source_text=chunk.source_text,
            translated_text=chunk.translated_text,
            direct_translation=chunk.direct_translation or chunk.translated_text,
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

    def rollback(self, chunk_id: str, revision: int) -> Optional[CorrectionEvent]:
        history = self._history.get(chunk_id)
        if not history:
            return None
        previous = history[-1]
        target = previous
        for item in reversed(history):
            if item.revision <= revision:
                target = item
                break
        if target.revision == previous.revision:
            return None
        return CorrectionEvent(
            chunk_id=target.chunk_id,
            previous_revision=previous.revision,
            current_revision=target.revision,
            source_text=target.source_text,
            translated_text=target.translated_text,
            direct_translation=target.direct_translation,
            is_final=target.is_final,
        )

    def correction_payload(self, event: CorrectionEvent) -> dict:
        return {
            "type": "correction",
            "session_id": "",
            "payload": {
                "chunk_id": event.chunk_id,
                "previousRevision": event.previous_revision,
                "currentRevision": event.current_revision,
                "sourceText": event.source_text,
                "translatedText": event.translated_text,
                "directTranslation": event.direct_translation,
                "isFinal": event.is_final,
            },
        }


revision_manager = RevisionManager()
