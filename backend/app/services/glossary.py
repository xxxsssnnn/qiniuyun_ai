from dataclasses import dataclass, field
from typing import Dict, List


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
