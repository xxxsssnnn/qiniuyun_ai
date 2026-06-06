from dataclasses import dataclass, field
from typing import Dict, List

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.glossary import GlossaryItem


@dataclass
class GlossaryEntry:
    source: str
    target: str
    note: str = ""


class GlossaryManager:
    def __init__(self) -> None:
        self._entries: Dict[str, GlossaryEntry] = {}
        self._context_history: Dict[str, List[str]] = {}

    def add_entry(self, source: str, target: str, note: str = "") -> GlossaryEntry:
        entry = GlossaryEntry(source=source.lower(), target=target, note=note)
        self._entries[entry.source] = entry
        return entry

    def update_entry(self, source: str, target: str, note: str = "") -> GlossaryEntry | None:
        key = source.lower()
        if key not in self._entries:
            return None
        entry = GlossaryEntry(source=key, target=target, note=note)
        self._entries[key] = entry
        return entry

    def add_entry_db(self, session: Session, source: str, target: str, note: str = "") -> GlossaryEntry:
        item = session.scalar(select(GlossaryItem).where(GlossaryItem.source == source.lower()))
        if item:
            item.target = target
            item.note = note
        else:
            item = GlossaryItem(source=source.lower(), target=target, note=note)
            session.add(item)
        session.commit()
        session.refresh(item)
        entry = GlossaryEntry(source=item.source, target=item.target, note=item.note or "")
        self._entries[entry.source] = entry
        return entry

    def update_entry_db(self, session: Session, source: str, target: str, note: str = "") -> GlossaryEntry | None:
        item = session.scalar(select(GlossaryItem).where(GlossaryItem.source == source.lower()))
        if not item:
            return None
        item.target = target
        item.note = note
        session.commit()
        session.refresh(item)
        entry = GlossaryEntry(source=item.source, target=item.target, note=item.note or "")
        self._entries[entry.source] = entry
        return entry

    def delete_entry_db(self, session: Session, source: str) -> bool:
        item = session.scalar(select(GlossaryItem).where(GlossaryItem.source == source.lower()))
        if not item:
            return False
        session.delete(item)
        session.commit()
        self._entries.pop(source.lower(), None)
        return True

    def load_entries_from_db(self, connection) -> None:
        session = Session(bind=connection)
        try:
            items = session.scalars(select(GlossaryItem)).all()
            for item in items:
                self._entries[item.source] = GlossaryEntry(source=item.source, target=item.target, note=item.note or "")
        finally:
            session.close()

    def remove_entry(self, source: str) -> None:
        self._entries.pop(source.lower(), None)

    def get_entry(self, source: str) -> GlossaryEntry | None:
        return self._entries.get(source.lower())

    def list_entries(self) -> list[GlossaryEntry]:
        return list(self._entries.values())

    def remember_context(self, session_id: str, text: str, limit: int = 12) -> list[str]:
        history = self._context_history.setdefault(session_id, [])
        history.append(text)
        if len(history) > limit:
            del history[:-limit]
        return list(history)

    def get_context(self, session_id: str) -> list[str]:
        return list(self._context_history.get(session_id, []))

    def apply_glossary(self, text: str) -> str:
        result = text
        for entry in self._entries.values():
            if entry.source and entry.source in result.lower():
                result = result.replace(entry.source, entry.target)
                result = result.replace(entry.source.title(), entry.target)
        return result


glossary_manager = GlossaryManager()
