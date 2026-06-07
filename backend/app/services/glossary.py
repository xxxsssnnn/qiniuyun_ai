import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.glossary import GlossaryItem


@dataclass
class GlossaryEntry:
    source: str
    target: str
    note: str = ""


class GlossaryConflictError(ValueError):
    pass


class GlossaryManager:
    def __init__(self) -> None:
        self._entries: Dict[str, GlossaryEntry] = {}
        self._context_history: Dict[str, List[str]] = {}

    @staticmethod
    def normalize_source(source: str) -> str:
        return " ".join(source.strip().split()).casefold()

    @staticmethod
    def _normalize_value(value: str) -> str:
        return " ".join(value.strip().split())

    @staticmethod
    def _term_pattern(source: str) -> re.Pattern[str]:
        escaped = re.escape(source)
        prefix = r"(?<!\w)" if source[0].isalnum() else ""
        suffix = r"(?!\w)" if source[-1].isalnum() else ""
        return re.compile(f"{prefix}{escaped}{suffix}", re.IGNORECASE)

    def _build_entry(self, source: str, target: str, note: str = "") -> GlossaryEntry:
        normalized_source = self.normalize_source(source)
        normalized_target = self._normalize_value(target)
        normalized_note = note.strip()
        if not normalized_source or not normalized_target:
            raise ValueError("Glossary source and target cannot be empty")
        return GlossaryEntry(
            source=normalized_source,
            target=normalized_target,
            note=normalized_note,
        )

    def add_entry(self, source: str, target: str, note: str = "") -> GlossaryEntry:
        entry = self._build_entry(source, target, note)
        self._entries[entry.source] = entry
        return entry

    def update_entry(self, source: str, target: str, note: str = "") -> Optional[GlossaryEntry]:
        key = self.normalize_source(source)
        if key not in self._entries:
            return None
        entry = self._build_entry(key, target, note)
        self._entries[key] = entry
        return entry

    def add_entry_db(self, session: Session, source: str, target: str, note: str = "") -> GlossaryEntry:
        entry = self._build_entry(source, target, note)
        item = session.scalar(select(GlossaryItem).where(GlossaryItem.source == entry.source))
        if item:
            item.target = entry.target
            item.note = entry.note
        else:
            item = GlossaryItem(
                source=entry.source,
                target=entry.target,
                note=entry.note,
            )
            session.add(item)
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise GlossaryConflictError("Glossary source already exists") from exc
        session.refresh(item)
        entry = GlossaryEntry(source=item.source, target=item.target, note=item.note or "")
        self._entries[entry.source] = entry
        return entry

    def update_entry_db(self, session: Session, source: str, target: str, note: str = "") -> Optional[GlossaryEntry]:
        key = self.normalize_source(source)
        entry = self._build_entry(key, target, note)
        item = session.scalar(select(GlossaryItem).where(GlossaryItem.source == key))
        if not item:
            return None
        item.target = entry.target
        item.note = entry.note
        session.commit()
        session.refresh(item)
        entry = GlossaryEntry(source=item.source, target=item.target, note=item.note or "")
        self._entries[entry.source] = entry
        return entry

    def rename_entry_db(
        self,
        session: Session,
        source: str,
        new_source: str,
        target: str,
        note: str = "",
    ) -> Optional[GlossaryEntry]:
        old_key = self.normalize_source(source)
        entry = self._build_entry(new_source, target, note)
        item = session.scalar(select(GlossaryItem).where(GlossaryItem.source == old_key))
        if not item:
            return None
        duplicate = session.scalar(
            select(GlossaryItem).where(
                GlossaryItem.source == entry.source,
                GlossaryItem.id != item.id,
            )
        )
        if duplicate:
            raise GlossaryConflictError("Glossary source already exists")
        item.source = entry.source
        item.target = entry.target
        item.note = entry.note
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise GlossaryConflictError("Glossary source already exists") from exc
        session.refresh(item)
        self._entries.pop(old_key, None)
        renamed = GlossaryEntry(
            source=item.source,
            target=item.target,
            note=item.note or "",
        )
        self._entries[renamed.source] = renamed
        return renamed

    def delete_entry_db(self, session: Session, source: str) -> bool:
        key = self.normalize_source(source)
        item = session.scalar(select(GlossaryItem).where(GlossaryItem.source == key))
        if not item:
            return False
        session.delete(item)
        session.commit()
        self._entries.pop(key, None)
        return True

    def load_entries_from_db(self, connection) -> None:
        session = Session(bind=connection)
        try:
            items = session.scalars(select(GlossaryItem)).all()
            self._entries.clear()
            for item in items:
                entry = self._build_entry(item.source, item.target, item.note or "")
                self._entries[entry.source] = entry
        finally:
            session.close()

    def remove_entry(self, source: str) -> None:
        self._entries.pop(self.normalize_source(source), None)

    def get_entry(self, source: str) -> Optional[GlossaryEntry]:
        return self._entries.get(self.normalize_source(source))

    def list_entries(self) -> List[GlossaryEntry]:
        return sorted(self._entries.values(), key=lambda entry: entry.source)

    def matching_entries(self, text: str) -> List[GlossaryEntry]:
        matches = [
            entry
            for entry in self._entries.values()
            if self._term_pattern(entry.source).search(text)
        ]
        return sorted(matches, key=lambda entry: (-len(entry.source), entry.source))

    def format_prompt(self, text: str = "", limit: int = 30) -> str:
        entries = self.matching_entries(text) if text else self.list_entries()
        lines = [
            f"- {entry.source} => {entry.target}"
            + (f" ({entry.note})" if entry.note else "")
            for entry in entries[:limit]
        ]
        return "\n".join(lines)

    def remember_context(self, session_id: str, text: str, limit: int = 12) -> List[str]:
        history = self._context_history.setdefault(session_id, [])
        history.append(text)
        if len(history) > limit:
            del history[:-limit]
        return list(history)

    def get_context(self, session_id: str) -> List[str]:
        return list(self._context_history.get(session_id, []))

    def apply_glossary(self, text: str) -> str:
        result = text
        for entry in self.matching_entries(text):
            result = self._term_pattern(entry.source).sub(
                lambda _: entry.target,
                result,
            )
        return result


glossary_manager = GlossaryManager()
