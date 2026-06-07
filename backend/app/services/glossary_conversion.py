from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.glossary_conversion import GlossaryConversionRecord
from app.services.glossary import glossary_manager
from app.services.streaming import TranscriptChunk


@dataclass
class GlossaryConversion:
    id: int
    session_id: str
    chunk_id: str
    glossary_source: str
    glossary_target: str
    before_text: str
    converted_text: str
    active: bool
    created_at: str
    updated_at: str


class GlossaryConversionStore:
    def record_for_chunk(self, chunk: TranscriptChunk) -> list[GlossaryConversion]:
        matches = glossary_manager.matching_entries(chunk.source_text)
        if not matches or not chunk.translated_text:
            return []

        conversions: list[GlossaryConversion] = []
        with SessionLocal() as db:
            for entry in matches:
                if entry.target not in chunk.translated_text:
                    continue
                existing = db.execute(
                    select(GlossaryConversionRecord).where(
                        GlossaryConversionRecord.session_id == chunk.session_id,
                        GlossaryConversionRecord.chunk_id == chunk.chunk_id,
                        GlossaryConversionRecord.glossary_source == entry.source,
                        GlossaryConversionRecord.glossary_target == entry.target,
                    )
                ).scalar_one_or_none()
                if existing is None:
                    existing = GlossaryConversionRecord(
                        session_id=chunk.session_id,
                        chunk_id=chunk.chunk_id,
                        glossary_source=entry.source,
                        glossary_target=entry.target,
                        before_text=chunk.direct_translation or chunk.source_text,
                        converted_text=chunk.translated_text,
                        active=True,
                    )
                    db.add(existing)
                else:
                    existing.converted_text = chunk.translated_text
                conversions.append(self._to_dataclass(existing))
            db.commit()
            return self.list_chunk(chunk.session_id, chunk.chunk_id)

    def list_session(self, session_id: str) -> list[GlossaryConversion]:
        with SessionLocal() as db:
            records = db.execute(
                select(GlossaryConversionRecord)
                .where(GlossaryConversionRecord.session_id == session_id)
                .order_by(GlossaryConversionRecord.updated_at.desc())
            ).scalars().all()
            return [self._to_dataclass(record) for record in records]

    def list_chunk(self, session_id: str, chunk_id: str) -> list[GlossaryConversion]:
        with SessionLocal() as db:
            records = db.execute(
                select(GlossaryConversionRecord)
                .where(
                    GlossaryConversionRecord.session_id == session_id,
                    GlossaryConversionRecord.chunk_id == chunk_id,
                )
                .order_by(GlossaryConversionRecord.id.asc())
            ).scalars().all()
            return [self._to_dataclass(record) for record in records]

    def get(self, conversion_id: int) -> GlossaryConversion | None:
        with SessionLocal() as db:
            record = db.get(GlossaryConversionRecord, conversion_id)
            return self._to_dataclass(record) if record else None

    def set_active(self, conversion_id: int, active: bool) -> GlossaryConversion | None:
        with SessionLocal() as db:
            record = db.get(GlossaryConversionRecord, conversion_id)
            if record is None:
                return None
            record.active = active
            db.commit()
            db.refresh(record)
            return self._to_dataclass(record)

    def delete(self, conversion_id: int) -> bool:
        with SessionLocal() as db:
            record = db.get(GlossaryConversionRecord, conversion_id)
            if record is None:
                return False
            db.delete(record)
            db.commit()
            return True

    def delete_session(self, db: Session, session_id: str) -> None:
        records = db.execute(
            select(GlossaryConversionRecord).where(
                GlossaryConversionRecord.session_id == session_id
            )
        ).scalars().all()
        for record in records:
            db.delete(record)

    def delete_chunk(self, db: Session, chunk_id: str) -> None:
        records = db.execute(
            select(GlossaryConversionRecord).where(
                GlossaryConversionRecord.chunk_id == chunk_id
            )
        ).scalars().all()
        for record in records:
            db.delete(record)

    def _to_dataclass(self, record: GlossaryConversionRecord) -> GlossaryConversion:
        return GlossaryConversion(
            id=record.id or 0,
            session_id=record.session_id,
            chunk_id=record.chunk_id,
            glossary_source=record.glossary_source,
            glossary_target=record.glossary_target,
            before_text=record.before_text,
            converted_text=record.converted_text,
            active=record.active,
            created_at=record.created_at.isoformat() if record.created_at else "",
            updated_at=record.updated_at.isoformat() if record.updated_at else "",
        )


def conversion_to_dict(conversion: GlossaryConversion) -> dict:
    return asdict(conversion)


glossary_conversion_store = GlossaryConversionStore()
