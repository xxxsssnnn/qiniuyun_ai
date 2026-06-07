import itertools
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Optional

from app.services.asr import ASRProvider, ASRResult
from app.services.connection_manager import ConnectionManager
from app.services.glossary import glossary_manager
from app.services.revision_manager import revision_manager
from app.services.streaming import TranscriptBuffer, TranscriptChunk
from app.services.translation import TranslationProvider
from app.services.tts import TTSProvider


@dataclass
class TranscriptEvent:
    chunk_id: str
    source_text: str
    translated_text: str
    is_final: bool
    revision: int = 0


@dataclass
class FinalizedSegment:
    chunk_id: str
    source_text: str
    translated_text: str
    finalized_at: float


class TranscriptionProcessor:
    def __init__(
        self,
        manager: ConnectionManager,
        buffer: TranscriptBuffer,
        asr_provider: ASRProvider,
        translation_provider: TranslationProvider,
        tts_provider: Optional[TTSProvider] = None,
    ) -> None:
        self.manager = manager
        self.buffer = buffer
        self.asr_provider = asr_provider
        self.translation_provider = translation_provider
        self.tts_provider = tts_provider
        self.target_language = os.getenv("TARGET_LANGUAGE", "zh")
        self._counter = itertools.count(1)
        self._active_chunk_ids: Dict[str, str] = {}
        self._active_prefixes: Dict[str, tuple[str, str]] = {}
        self._finalized_segments: Dict[str, FinalizedSegment] = {}
        self._revisions: Dict[str, int] = {}
        self.continuation_window_seconds = 2.5

    @staticmethod
    def _has_sentence_ending(text: str) -> bool:
        return text.rstrip().endswith((".", "?", "!", "。", "？", "！"))

    def _continuation_for(self, session_id: str) -> FinalizedSegment | None:
        previous = self._finalized_segments.get(session_id)
        if previous is None or self._has_sentence_ending(previous.source_text):
            return None
        if time.monotonic() - previous.finalized_at > self.continuation_window_seconds:
            return None
        return previous

    @staticmethod
    def _join_segments(previous: str, current: str) -> str:
        previous = previous.strip()
        current = current.strip()
        if not previous:
            return current
        if not current:
            return previous
        joins_without_space = (
            previous[-1:].isspace()
            or current[:1] in ",.!?;:，。！？；："
            or bool(re.search(r"[\u3400-\u9fff]$", previous))
            or bool(re.match(r"^[\u3400-\u9fff]", current))
        )
        separator = "" if joins_without_space else " "
        return f"{previous}{separator}{current}"

    async def handle_asr_result(
        self,
        session_id: str,
        asr_result: ASRResult,
        byte_length: int = 0,
    ) -> None:
        if asr_result.error:
            await self.manager.broadcast(
                session_id,
                {
                    "type": "error",
                    "session_id": session_id,
                    "payload": {"message": asr_result.error},
                },
            )
            return
        index = next(self._counter)
        if not asr_result.text.strip() and not (asr_result.translated_text or "").strip():
            return
        if asr_result.text.strip():
            glossary_manager.remember_context(session_id, asr_result.text)
        is_final = asr_result.is_final
        chunk_id = self._active_chunk_ids.get(session_id)
        if not chunk_id:
            continuation = self._continuation_for(session_id)
            if continuation:
                chunk_id = continuation.chunk_id
                self._active_prefixes[session_id] = (
                    continuation.source_text,
                    continuation.translated_text,
                )
            else:
                chunk_id = f"{session_id}-chunk-{index}"
                self._active_prefixes.pop(session_id, None)
            self._active_chunk_ids[session_id] = chunk_id

        current_revision = self._revisions.get(chunk_id, 0)
        if is_final or asr_result.revision > current_revision:
            current_revision += 1
        self._revisions[chunk_id] = current_revision

        if asr_result.translated_text is not None:
            translated_text = asr_result.translated_text
        else:
            translation_result = await self.translation_provider.translate(
                asr_result.text,
                source_language=asr_result.language,
                target_language=self.target_language,
                session_id=session_id,
            )
            translated_text = translation_result.translated_text
        source_prefix, translation_prefix = self._active_prefixes.get(
            session_id,
            ("", ""),
        )
        source_text = self._join_segments(source_prefix, asr_result.text)
        translated_text = self._join_segments(
            translation_prefix,
            translated_text,
        )
        if self.tts_provider and is_final:
            await self.tts_provider.speak(translated_text, language=self.target_language)
        event = TranscriptEvent(
            chunk_id=chunk_id,
            source_text=source_text,
            translated_text=translated_text,
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
            self._active_prefixes.pop(session_id, None)
            self._finalized_segments[session_id] = FinalizedSegment(
                chunk_id=chunk_id,
                source_text=event.source_text,
                translated_text=event.translated_text,
                finalized_at=time.monotonic(),
            )

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
                    "byteLength": byte_length,
                    "confidence": asr_result.confidence,
                    "language": asr_result.language,
                },
            },
        )

    async def handle_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        asr_result = await self.asr_provider.transcribe(chunk, session_id)
        await self.handle_asr_result(session_id, asr_result, len(chunk))

    async def close_session(self, session_id: str) -> None:
        await self.asr_provider.close_session(session_id)
