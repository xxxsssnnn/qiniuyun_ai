from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.transcript import TranscriptRecord
from app.models.transcript_revision import TranscriptRevision
from app.models.transcript_session import TranscriptSession
from app.services.glossary_conversion import glossary_conversion_store
from app.services.streaming import TranscriptChunk


@dataclass
class SessionSummary:
    session_id: str
    name: str
    chunk_count: int
    correction_count: int
    created_at: str
    latest_updated_at: str


class TranscriptStore:
    def save_chunk(self, chunk: TranscriptChunk) -> None:
        with SessionLocal() as db:
            self._ensure_session(db, chunk.session_id)
            self._save_revision(db, chunk)
            self._upsert(db, chunk)
            db.commit()
        chunk.glossary_conversions = [
            asdict(item)
            for item in glossary_conversion_store.record_for_chunk(chunk)
        ]

    def _save_revision(self, db: Session, chunk: TranscriptChunk) -> None:
        existing = db.execute(
            select(TranscriptRevision).where(
                TranscriptRevision.chunk_id == chunk.chunk_id,
                TranscriptRevision.revision == chunk.revision,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return
        current = db.execute(
            select(TranscriptRecord).where(
                TranscriptRecord.chunk_id == chunk.chunk_id
            )
        ).scalar_one_or_none()
        direct_translation = (
            chunk.direct_translation
            or (
                current.direct_translation or current.translated_text
                if current is not None
                else ""
            )
            or chunk.translated_text
        )
        db.add(
            TranscriptRevision(
                session_id=chunk.session_id,
                chunk_id=chunk.chunk_id,
                source_text=chunk.source_text,
                translated_text=chunk.translated_text,
                direct_translation=direct_translation,
                is_final=chunk.is_final,
                revision=chunk.revision,
                auto_correction=chunk.auto_correction,
                correction_reasons=json.dumps(
                    chunk.correction_reasons,
                    ensure_ascii=False,
                ),
            )
        )

    def create_session(self, session_id: str, name: str) -> SessionSummary:
        normalized_name = name.strip() or "未命名会话"
        with SessionLocal() as db:
            existing = db.get(TranscriptSession, session_id)
            if existing is None:
                existing = TranscriptSession(
                    session_id=session_id,
                    name=normalized_name,
                )
                db.add(existing)
            else:
                existing.name = normalized_name
            db.commit()
        return self.get_session(session_id) or SessionSummary(
            session_id=session_id,
            name=normalized_name,
            chunk_count=0,
            correction_count=0,
            created_at="",
            latest_updated_at="",
        )

    def rename_session(self, session_id: str, name: str) -> SessionSummary | None:
        normalized_name = name.strip()
        if not normalized_name:
            return None
        with SessionLocal() as db:
            session = db.get(TranscriptSession, session_id)
            if session is None:
                session = TranscriptSession(
                    session_id=session_id,
                    name=normalized_name,
                )
                db.add(session)
            else:
                session.name = normalized_name
            db.commit()
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> SessionSummary | None:
        return next(
            (
                session
                for session in self.list_sessions()
                if session.session_id == session_id
            ),
            None,
        )

    def _ensure_session(self, db: Session, session_id: str) -> TranscriptSession:
        session = db.get(TranscriptSession, session_id)
        if session is None:
            session = TranscriptSession(
                session_id=session_id,
                name=self._default_session_name(session_id),
            )
            db.add(session)
        return session

    def _default_session_name(self, session_id: str) -> str:
        if session_id == "demo-session":
            return "默认会话"
        return f"会话 {session_id[-8:]}"

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
                direct_translation=chunk.direct_translation or chunk.translated_text,
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
        record.direct_translation = (
            chunk.direct_translation
            or record.direct_translation
            or chunk.translated_text
        )
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

    def list_revisions(
        self,
        session_id: str,
        chunk_id: str | None = None,
    ) -> list[TranscriptChunk]:
        with SessionLocal() as db:
            statement = select(TranscriptRevision).where(
                TranscriptRevision.session_id == session_id
            )
            if chunk_id:
                statement = statement.where(
                    TranscriptRevision.chunk_id == chunk_id
                )
            records = db.execute(
                statement.order_by(
                    TranscriptRevision.id.desc(),
                )
            ).scalars().all()
            return [self._revision_to_chunk(record) for record in records]

    def latest_chunk(self, session_id: str | None = None) -> TranscriptChunk | None:
        with SessionLocal() as db:
            statement = select(TranscriptRecord)
            if session_id:
                statement = statement.where(TranscriptRecord.session_id == session_id)
            record = db.execute(statement.order_by(TranscriptRecord.id.desc())).scalars().first()
            return self._to_chunk(record) if record else None

    def delete_session(self, session_id: str) -> bool:
        with SessionLocal() as db:
            session = db.get(TranscriptSession, session_id)
            chunks = db.execute(
                select(TranscriptRecord).where(
                    TranscriptRecord.session_id == session_id
                )
            ).scalars().all()
            revisions = db.execute(
                select(TranscriptRevision).where(
                    TranscriptRevision.session_id == session_id
                )
            ).scalars().all()
            if session is None and not chunks and not revisions:
                return False
            glossary_conversion_store.delete_session(db, session_id)
            for item in revisions:
                db.delete(item)
            for item in chunks:
                db.delete(item)
            if session is not None:
                db.delete(session)
            db.commit()
            return True

    def delete_chunk(self, session_id: str, chunk_id: str) -> bool:
        with SessionLocal() as db:
            record = db.execute(
                select(TranscriptRecord).where(
                    TranscriptRecord.session_id == session_id,
                    TranscriptRecord.chunk_id == chunk_id,
                )
            ).scalar_one_or_none()
            revisions = db.execute(
                select(TranscriptRevision).where(
                    TranscriptRevision.session_id == session_id,
                    TranscriptRevision.chunk_id == chunk_id,
                )
            ).scalars().all()
            if record is None and not revisions:
                return False
            glossary_conversion_store.delete_chunk(db, chunk_id)
            for item in revisions:
                db.delete(item)
            if record is not None:
                db.delete(record)
            db.commit()
            return True

    def delete_revision(self, session_id: str, chunk_id: str, revision: int) -> bool:
        with SessionLocal() as db:
            record = db.execute(
                select(TranscriptRevision).where(
                    TranscriptRevision.session_id == session_id,
                    TranscriptRevision.chunk_id == chunk_id,
                    TranscriptRevision.revision == revision,
                )
            ).scalar_one_or_none()
            if record is None:
                return False
            db.delete(record)
            db.commit()
            return True

    def list_sessions(self) -> list[SessionSummary]:
        with SessionLocal() as db:
            records = db.execute(
                select(TranscriptRecord).order_by(TranscriptRecord.updated_at.desc())
            ).scalars().all()
            sessions = db.execute(
                select(TranscriptSession).order_by(TranscriptSession.updated_at.desc())
            ).scalars().all()
        grouped: dict[str, list[TranscriptRecord]] = {}
        for record in records:
            grouped.setdefault(record.session_id, []).append(record)

        metadata = {session.session_id: session for session in sessions}
        all_session_ids = set(metadata) | set(grouped)
        summaries: list[SessionSummary] = []
        for session_id in all_session_ids:
            items = grouped.get(session_id, [])
            final_items = [item for item in items if item.is_final]
            session = metadata.get(session_id)
            latest_record = max(items, key=lambda item: item.updated_at) if items else None
            latest_at = (
                latest_record.updated_at
                if latest_record is not None
                else session.updated_at if session is not None else None
            )
            created_at = (
                session.created_at
                if session is not None
                else min(items, key=lambda item: item.created_at).created_at
                if items
                else None
            )
            summaries.append(
                SessionSummary(
                    session_id=session_id,
                    name=(
                        session.name
                        if session is not None
                        else self._default_session_name(session_id)
                    ),
                    chunk_count=len(final_items),
                    correction_count=sum(1 for item in final_items if item.auto_correction),
                    created_at=created_at.isoformat() if created_at else "",
                    latest_updated_at=latest_at.isoformat() if latest_at else "",
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
        chunk = TranscriptChunk(
            chunk_id=record.chunk_id,
            source_text=record.source_text,
            translated_text=record.translated_text,
            direct_translation=record.direct_translation or record.translated_text,
            is_final=record.is_final,
            session_id=record.session_id,
            revision=record.revision,
            auto_correction=record.auto_correction,
            correction_reasons=reasons if isinstance(reasons, list) else [],
        )
        chunk.glossary_conversions = [
            asdict(item)
            for item in glossary_conversion_store.list_chunk(
                record.session_id,
                record.chunk_id,
            )
        ]
        return chunk

    def _revision_to_chunk(self, record: TranscriptRevision) -> TranscriptChunk:
        try:
            reasons = json.loads(record.correction_reasons or "[]")
        except json.JSONDecodeError:
            reasons = []
        chunk = TranscriptChunk(
            chunk_id=record.chunk_id,
            source_text=record.source_text,
            translated_text=record.translated_text,
            direct_translation=record.direct_translation or record.translated_text,
            is_final=record.is_final,
            session_id=record.session_id,
            revision=record.revision,
            auto_correction=record.auto_correction,
            correction_reasons=reasons if isinstance(reasons, list) else [],
        )
        chunk.glossary_conversions = [
            asdict(item)
            for item in glossary_conversion_store.list_chunk(
                record.session_id,
                record.chunk_id,
            )
        ]
        return chunk
        chunk.glossary_conversions = [
            asdict(item)
            for item in glossary_conversion_store.list_chunk(
                record.session_id,
                record.chunk_id,
            )
        ]
        return chunk

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
