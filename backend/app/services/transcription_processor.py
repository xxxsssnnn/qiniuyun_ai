import itertools
from dataclasses import dataclass

from app.services.connection_manager import ConnectionManager
from app.services.streaming import TranscriptBuffer, TranscriptChunk


@dataclass
class TranscriptEvent:
    chunk_id: str
    source_text: str
    translated_text: str
    is_final: bool
    revision: int = 0


class MockTranscriptionProcessor:
    def __init__(self, manager: ConnectionManager, buffer: TranscriptBuffer) -> None:
        self.manager = manager
        self.buffer = buffer
        self._counter = itertools.count(1)

    async def handle_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        index = next(self._counter)
        source_text = f"[ASR] detected speech segment {index}"
        translated_text = f"[翻译] 检测到第 {index} 段语音"
        is_final = index % 3 == 0
        event = TranscriptEvent(
            chunk_id=f"chunk-{index}",
            source_text=source_text,
            translated_text=translated_text,
            is_final=is_final,
        )
        self.buffer.append(
            TranscriptChunk(
                chunk_id=event.chunk_id,
                source_text=event.source_text,
                translated_text=event.translated_text,
                is_final=event.is_final,
            )
        )
        await self.manager.broadcast(
            session_id,
            {
                "type": "chunk" if not is_final else "revision",
                "session_id": session_id,
                "payload": {
                    "chunk_id": event.chunk_id,
                    "sourceText": event.source_text,
                    "translatedText": event.translated_text,
                    "isFinal": event.is_final,
                    "revision": event.revision,
                    "byteLength": len(chunk),
                },
            },
        )
