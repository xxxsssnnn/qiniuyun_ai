from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class AudioSessionState:
    session_id: str
    is_recording: bool = False
    audio_chunks: List[bytes] = field(default_factory=list)
    audio_chunk_count: int = 0

    def start(self) -> None:
        self.is_recording = True

    def stop(self) -> None:
        self.is_recording = False

    def append_chunk(self, chunk: bytes) -> None:
        self.audio_chunks.append(chunk)
        self.audio_chunk_count += 1


class AudioSessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, AudioSessionState] = {}

    def get_or_create(self, session_id: str) -> AudioSessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = AudioSessionState(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> AudioSessionState | None:
        return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


audio_sessions = AudioSessionStore()
