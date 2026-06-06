import itertools
from dataclasses import dataclass

from app.services.asr import ASRProvider
from app.services.connection_manager import ConnectionManager
from app.services.streaming import TranscriptBuffer, TranscriptChunk
from app.services.translation import TranslationProvider


@dataclass
class TranscriptEvent:
    chunk_id: str
    source_text: str
    translated_text: str
    is_final: bool
    revision: int = 0


class TranscriptionProcessor:
    def __init__(self, manager: ConnectionManager, buffer: TranscriptBuffer, asr_provider: ASRProvider, translation_provider: TranslationProvider) -> None:
        self.manager = manager
        self.buffer = buffer
        self.asr_provider = asr_provider
        self.translation_provider = translation_provider
        self._counter = itertools.count(1)

    async def handle_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        index = next(self._counter)
        asr_result = await self.asr_provider.transcribe(chunk)
        translation_result = await self.translation_provider.translate(asr_result.text)
        is_final = asr_result.is_final or index % 3 == 0
        event = TranscriptEvent(
            chunk_id=f"chunk-{index}",
            source_text=asr_result.text,
            translated_text=translation_result.translated_text,
            is_final=is_final,
            revision=asr_result.revision,
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
