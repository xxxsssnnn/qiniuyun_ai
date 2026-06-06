from dataclasses import dataclass

from app.services.asr import ASRProvider, MockASRProvider
from app.services.connection_manager import ConnectionManager
from app.services.streaming import TranscriptBuffer, TranscriptChunk


@dataclass
class TranscriptEvent:
    chunk_id: str
    source_text: str
    translated_text: str
    is_final: bool
    revision: int = 0


class TranscriptionProcessor:
    def __init__(self, manager: ConnectionManager, buffer: TranscriptBuffer, asr_provider: ASRProvider | None = None) -> None:
        self.manager = manager
        self.buffer = buffer
        self.asr_provider = asr_provider or MockASRProvider()
        self._counter = 0

    async def handle_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        self._counter += 1
        result = await self.asr_provider.transcribe(chunk, session_id)
        translated_text = f"[翻译] {result.text.replace('[ASR] ', '')}"
        event = TranscriptEvent(
            chunk_id=f"chunk-{self._counter}",
            source_text=result.text,
            translated_text=translated_text,
            is_final=result.is_final,
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
                "type": "chunk" if not event.is_final else "revision",
                "session_id": session_id,
                "payload": {
                    "chunk_id": event.chunk_id,
                    "sourceText": event.source_text,
                    "translatedText": event.translated_text,
                    "isFinal": event.is_final,
                    "revision": event.revision,
                    "confidence": result.confidence,
                    "byteLength": len(chunk),
                },
            },
        )
