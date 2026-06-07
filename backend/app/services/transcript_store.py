from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.transcript import TranscriptRecord
from app.services.streaming import TranscriptChunk


@dataclass
class SessionSummary:
    session_id: str
    chunk_count: int
    correction_count: int
    latest_updated_at: str


class TranscriptStore:
    def save_chunk(self, chunk: TranscriptChunk) -> None:
        with SessionLocal() as db:
            self._upsert(db, chunk)
            db.commit()

    def _upsert(self, db: Session, chunk: TranscriptChunk) -> TranscriptRecord:
        record = db.execute(
            select(TranscriptRecord).where(TranscriptRecord.chunk_id == chunk.chunk_id)
        ).scalar_one_or_none()
        reasons = json.dumps(chunk.correction_reasons, ensure_ascii=False)
        if record is None:
            record = TranscriptRecord(
                session_id=chunk.session_id,
                chunk_id=chunk.chunk_id,
                source_text=chunk.source_text,
                translated_text=chunk.translated_text,
                is_final=chunk.is_final,
                revision=chunk.revision,
                auto_correction=chunk.auto_correction,
                correction_reasons=reasons,
            )
            db.add(record)
            return record

        record.session_id = chunk.session_id
        record.source_text = chunk.source_text
        record.translated_text = chunk.translated_text
        record.is_final = chunk.is_final
        record.revision = chunk.revision
        record.auto_correction = chunk.auto_correction
        record.correction_reasons = reasons
        return record

    def list_chunks(self, session_id: str, final_only: bool = True) -> list[TranscriptChunk]:
        with SessionLocal() as db:
            statement = select(TranscriptRecord).where(TranscriptRecord.session_id == session_id)
            if final_only:
                statement = statement.where(TranscriptRecord.is_final.is_(True))
            records = db.execute(statement.order_by(TranscriptRecord.id.asc())).scalars().all()
            return [self._to_chunk(record) for record in records]

    def latest_chunk(self, session_id: str | None = None) -> TranscriptChunk | None:
        with SessionLocal() as db:
            statement = select(TranscriptRecord)
            if session_id:
                statement = statement.where(TranscriptRecord.session_id == session_id)
            record = db.execute(statement.order_by(TranscriptRecord.id.desc())).scalars().first()
            return self._to_chunk(record) if record else None

    def list_sessions(self) -> list[SessionSummary]:
        with SessionLocal() as db:
            records = db.execute(select(TranscriptRecord).order_by(TranscriptRecord.updated_at.desc())).scalars().all()
        grouped: dict[str, list[TranscriptRecord]] = {}
        for record in records:
            grouped.setdefault(record.session_id, []).append(record)

        summaries: list[SessionSummary] = []
        for session_id, items in grouped.items():
            final_items = [item for item in items if item.is_final]
            latest = max(items, key=lambda item: item.updated_at)
            summaries.append(
                SessionSummary(
                    session_id=session_id,
                    chunk_count=len(final_items),
                    correction_count=sum(1 for item in final_items if item.auto_correction),
                    latest_updated_at=latest.updated_at.isoformat() if latest.updated_at else "",
                )
            )
        return sorted(summaries, key=lambda item: item.latest_updated_at, reverse=True)

    def export_session(self, session_id: str, fmt: str = "json") -> str | list[dict]:
        chunks = self.list_chunks(session_id, final_only=True)
        if fmt == "srt":
            return self._to_srt(chunks)
        if fmt == "txt":
            return "\n\n".join(
                f"{index + 1}. {chunk.source_text}\n{chunk.translated_text}"
                for index, chunk in enumerate(chunks)
            )
        return [asdict(chunk) for chunk in chunks]

    def _to_chunk(self, record: TranscriptRecord) -> TranscriptChunk:
        try:
            reasons = json.loads(record.correction_reasons or "[]")
        except json.JSONDecodeError:
            reasons = []
        return TranscriptChunk(
            chunk_id=record.chunk_id,
            source_text=record.source_text,
            translated_text=record.translated_text,
            is_final=record.is_final,
            session_id=record.session_id,
            revision=record.revision,
            auto_correction=record.auto_correction,
            correction_reasons=reasons if isinstance(reasons, list) else [],
        )

    def _to_srt(self, chunks: Iterable[TranscriptChunk]) -> str:
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


transcript_store = TranscriptStore()
