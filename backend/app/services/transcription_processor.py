import itertools
from dataclasses import dataclass
from typing import Dict, Optional

from app.services.asr import ASRProvider
from app.services.asr_factory import get_asr_provider
from app.services.connection_manager import ConnectionManager
from app.services.glossary import glossary_manager
from app.services.revision_manager import revision_manager
from app.services.streaming import TranscriptBuffer, TranscriptChunk
from app.services.translation import TranslationProvider
from app.services.translation_factory import get_translation_provider
from app.services.tts import TTSProvider
from app.services.tts_factory import get_tts_provider


@dataclass
class TranscriptEvent:
    chunk_id: str
    source_text: str
    translated_text: str
    is_final: bool
    revision: int = 0


class TranscriptionProcessor:
    def __init__(
        self,
        manager: ConnectionManager,
        buffer: TranscriptBuffer,
        asr_provider: Optional[ASRProvider] = None,
        translation_provider: Optional[TranslationProvider] = None,
        tts_provider: Optional[TTSProvider] = None,
    ) -> None:
        self.manager = manager
        self.buffer = buffer
        self.asr_provider = asr_provider
        self.translation_provider = translation_provider
        self.tts_provider = tts_provider
        self._counter = itertools.count(1)
        self._active_chunk_ids: Dict[str, str] = {}
        self._revisions: Dict[str, int] = {}

    def refresh_providers(self) -> None:
        self.asr_provider = get_asr_provider()
        self.translation_provider = get_translation_provider()
        self.tts_provider = get_tts_provider()

    async def handle_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        self.refresh_providers()
        if self.asr_provider is None or self.translation_provider is None:
            self.refresh_providers()
        index = next(self._counter)
        asr_result = await self.asr_provider.transcribe(chunk, session_id)  # type: ignore[union-attr]
        glossary_manager.remember_context(session_id, asr_result.text)
        is_final = asr_result.is_final or index % 3 == 0
        chunk_id = self._active_chunk_ids.get(session_id)
        if not chunk_id:
            chunk_id = f"{session_id}-chunk-{index}"
            self._active_chunk_ids[session_id] = chunk_id

        current_revision = self._revisions.get(chunk_id, 0)
        if is_final or asr_result.revision > current_revision:
            current_revision += 1
        self._revisions[chunk_id] = current_revision

        translation_result = await self.translation_provider.translate(  # type: ignore[union-attr]
            asr_result.text,
            source_language=asr_result.language,
            target_language="zh",
            session_id=session_id,
        )
        if self.tts_provider and is_final:
            await self.tts_provider.speak(translation_result.translated_text)
        event = TranscriptEvent(
            chunk_id=chunk_id,
            source_text=asr_result.text,
            translated_text=translation_result.translated_text,
            is_final=is_final,
            revision=current_revision,
        )
        chunk_record = TranscriptChunk(
            chunk_id=event.chunk_id,
            source_text=event.source_text,
            translated_text=event.translated_text,
            is_final=event.is_final,
        )
        self.buffer.upsert(chunk_record)
        revision_manager.record(chunk_record, event.revision)
        if is_final:
            self._active_chunk_ids.pop(session_id, None)

        await self.manager.broadcast(
            session_id,
            {
                "type": "chunk" if event.revision == 0 else "revision",
                "session_id": session_id,
                "payload": {
                    "chunk_id": event.chunk_id,
                    "sourceText": event.source_text,
                    "translatedText": event.translated_text,
                    "isFinal": event.is_final,
                    "revision": event.revision,
                    "byteLength": len(chunk),
                    "confidence": asr_result.confidence,
                    "language": asr_result.language,
                },
            },
        )
