import asyncio
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
        self._revisions: Dict[str, int] = {}
        self._sentence_buffers: Dict[str, list[str]] = {}
        self._sentence_buffer_started_at: Dict[str, float] = {}
        self._min_translate_chars = int(os.getenv("MIN_TRANSLATE_CHARS", "28"))
        self._max_buffer_seconds = float(os.getenv("MAX_TRANSLATE_BUFFER_SECONDS", "1.2"))
        self._translation_timeout_seconds = float(os.getenv("TRANSLATION_TIMEOUT_SECONDS", "3.5"))

    def _should_flush_sentence_buffer(self, session_id: str, text: str) -> bool:
        compact_text = text.strip()
        if not compact_text:
            return False
        if re.search(r"[.!?。！？；;：:]$", compact_text):
            return True
        if len(compact_text) >= self._min_translate_chars:
            return True
        started_at = self._sentence_buffer_started_at.get(session_id)
        return started_at is not None and (time.monotonic() - started_at) >= self._max_buffer_seconds

    def _append_sentence_buffer(self, session_id: str, text: str) -> str | None:
        compact_text = text.strip()
        if not compact_text:
            return None
        buffer = self._sentence_buffers.setdefault(session_id, [])
        if not buffer:
            self._sentence_buffer_started_at[session_id] = time.monotonic()
        buffer.append(compact_text)
        buffered_text = " ".join(buffer).strip()
        if not self._should_flush_sentence_buffer(session_id, buffered_text):
            return None
        self._sentence_buffers.pop(session_id, None)
        self._sentence_buffer_started_at.pop(session_id, None)
        return buffered_text

    async def handle_asr_result(
        self,
        session_id: str,
        asr_result: ASRResult,
        byte_length: int = 0,
    ) -> None:
        index = next(self._counter)
        source_text = asr_result.text.strip()
        model_translated_text = (asr_result.translated_text or "").strip()
        if not source_text and not model_translated_text:
            return

        is_final = asr_result.is_final
        chunk_id = self._active_chunk_ids.get(session_id)
        if not chunk_id:
            chunk_id = f"{session_id}-chunk-{index}"
            self._active_chunk_ids[session_id] = chunk_id

        current_revision = self._revisions.get(chunk_id, 0)
        if is_final or asr_result.revision > current_revision:
            current_revision += 1
        self._revisions[chunk_id] = current_revision

        if source_text:
            await self.manager.broadcast(
                session_id,
                {
                    "type": "source_partial" if not is_final else "source_final",
                    "session_id": session_id,
                    "payload": {
                        "chunk_id": chunk_id,
                        "sourceText": source_text,
                        "isFinal": is_final,
                        "revision": current_revision,
                        "byteLength": byte_length,
                        "confidence": asr_result.confidence,
                        "language": asr_result.language,
                    },
                },
            )

        if not is_final:
            return

        translation_source_text = ""
        if source_text:
            glossary_manager.remember_context(session_id, source_text)
            buffered_text = self._append_sentence_buffer(session_id, source_text)
            self._active_chunk_ids.pop(session_id, None)
            if buffered_text is None:
                return
            translation_source_text = buffered_text
            chunk_id = f"{session_id}-chunk-{next(self._counter)}"
            current_revision = 1
            self._revisions[chunk_id] = current_revision
        else:
            translation_source_text = ""

        if translation_source_text:
            try:
                translation_result = await asyncio.wait_for(
                    self.translation_provider.translate(
                        translation_source_text,
                        source_language=asr_result.language,
                        target_language=self.target_language,
                        session_id=session_id,
                    ),
                    timeout=self._translation_timeout_seconds,
                )
                translated_text = translation_result.translated_text
            except asyncio.TimeoutError:
                translated_text = model_translated_text or "译文生成超时，请稍后查看原文。"
            except Exception:
                translated_text = model_translated_text or "译文生成失败，请稍后查看原文。"
        else:
            translated_text = model_translated_text

        if not translated_text and model_translated_text:
            translated_text = model_translated_text

        if self.tts_provider and translated_text:
            await self.tts_provider.speak(translated_text, language=self.target_language)
        event = TranscriptEvent(
            chunk_id=chunk_id,
            source_text=translation_source_text or asr_result.text,
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
        self._active_chunk_ids.pop(session_id, None)
        self._sentence_buffers.pop(session_id, None)
        self._sentence_buffer_started_at.pop(session_id, None)
        await self.asr_provider.close_session(session_id)
