import asyncio
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, Optional
from uuid import uuid4

from app.services.asr import ASRProvider, ASRResult
from app.services.auto_correction import auto_correction_engine
from app.services.connection_manager import ConnectionManager
from app.services.glossary import glossary_manager
from app.services.qwen_correction import qwen_correction_service
from app.services.revision_manager import CorrectionEvent, revision_manager
from app.services.streaming import TranscriptBuffer, TranscriptChunk
from app.services.transcript_store import transcript_store
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
        self._active_chunk_ids: Dict[str, str] = {}
        self._revisions: Dict[str, int] = {}
        self._sentence_buffers: Dict[str, list[str]] = {}
        self._sentence_buffer_started_at: Dict[str, float] = {}
        self._min_translate_chars = int(os.getenv("MIN_TRANSLATE_CHARS", "28"))
        self._max_buffer_seconds = float(os.getenv("MAX_TRANSLATE_BUFFER_SECONDS", "1.2"))
        self._translation_timeout_seconds = float(os.getenv("TRANSLATION_TIMEOUT_SECONDS", "3.5"))
        self._auto_correction_enabled = os.getenv("AUTO_CORRECTION_ENABLED", "true").lower() != "false"
        self._auto_correction_min_confidence = float(os.getenv("AUTO_CORRECTION_MIN_CONFIDENCE", "0.68"))
        self._context_correction_enabled = (
            os.getenv("QWEN_CONTEXT_CORRECTION_ENABLED", "true").lower() != "false"
        )
        self._context_correction_lock = asyncio.Lock()
        self._correction_tasks: set[asyncio.Task[None]] = set()

    def _new_chunk_id(self, session_id: str) -> str:
        return f"{session_id}-chunk-{uuid4().hex}"

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

    async def _translate_text(
        self,
        session_id: str,
        text: str,
        source_language: str,
        fallback_text: str = "",
    ) -> str:
        try:
            translation_result = await asyncio.wait_for(
                self.translation_provider.translate(
                    text,
                    source_language=source_language,
                    target_language=self.target_language,
                    session_id=session_id,
                ),
                timeout=self._translation_timeout_seconds,
            )
            return translation_result.translated_text
        except asyncio.TimeoutError:
            return fallback_text or "译文生成超时，请稍后查看原文。"
        except Exception:
            return fallback_text or "译文生成失败，请稍后查看原文。"

    async def _broadcast_auto_correction(
        self,
        session_id: str,
        chunk_id: str,
        previous_revision: int,
        current_revision: int,
        source_text: str,
        translated_text: str,
        direct_translation: str,
        is_final: bool,
        reasons: list[str],
    ) -> None:
        event = CorrectionEvent(
            chunk_id=chunk_id,
            previous_revision=previous_revision,
            current_revision=current_revision,
            source_text=source_text,
            translated_text=translated_text,
            direct_translation=direct_translation,
            is_final=is_final,
        )
        payload = revision_manager.correction_payload(event)
        payload["session_id"] = session_id
        payload["payload"]["revision"] = current_revision
        payload["payload"]["autoCorrection"] = True
        payload["payload"]["reasons"] = reasons
        latest_chunk = self.buffer.latest(session_id)
        payload["payload"]["glossaryConversions"] = (
            latest_chunk.glossary_conversions
            if latest_chunk and latest_chunk.chunk_id == chunk_id
            else []
        )
        await self.manager.broadcast(session_id, payload)

    async def _auto_correct_final_chunk(
        self,
        session_id: str,
        chunk_id: str,
        source_text: str,
        translated_text: str,
        asr_result: ASRResult,
        current_revision: int,
    ) -> tuple[str, str, int, list[str]]:
        if not self._auto_correction_enabled:
            return source_text, translated_text, current_revision, []

        correction = auto_correction_engine.correct(
            source_text=source_text,
            translated_text=translated_text,
            confidence=asr_result.confidence,
            force_review=asr_result.confidence < self._auto_correction_min_confidence,
        )
        if not correction.changed:
            return source_text, translated_text, current_revision, []

        corrected_translation = translated_text
        if correction.source_text != source_text or asr_result.confidence < self._auto_correction_min_confidence:
            corrected_translation = await self._translate_text(
                session_id,
                correction.source_text,
                asr_result.language,
                correction.translated_text or translated_text,
            )
            second_pass = auto_correction_engine.correct(
                source_text=correction.source_text,
                translated_text=corrected_translation,
                confidence=asr_result.confidence,
            )
            corrected_translation = second_pass.translated_text
            for reason in second_pass.reasons:
                if reason not in correction.reasons:
                    correction.reasons.append(reason)
        else:
            corrected_translation = correction.translated_text

        next_revision = current_revision + 1
        corrected_chunk = TranscriptChunk(
            chunk_id=chunk_id,
            source_text=correction.source_text,
            translated_text=corrected_translation,
            direct_translation=translated_text,
            is_final=True,
            session_id=session_id,
            revision=next_revision,
            auto_correction=True,
            correction_reasons=correction.reasons,
        )
        self.buffer.upsert(corrected_chunk)
        transcript_store.save_chunk(corrected_chunk)
        revision_manager.record(corrected_chunk, next_revision)
        await self._broadcast_auto_correction(
            session_id,
            chunk_id,
            current_revision,
            next_revision,
            correction.source_text,
            corrected_translation,
            translated_text,
            True,
            correction.reasons,
        )
        return correction.source_text, corrected_translation, next_revision, correction.reasons

    async def _review_context(self, session_id: str) -> None:
        if not self._context_correction_enabled or not qwen_correction_service.available:
            return
        async with self._context_correction_lock:
            session_chunks = self.buffer.list_session(session_id, final_only=True)
            corrections = await qwen_correction_service.review(session_chunks)
            for correction in corrections:
                current = next(
                    (
                        chunk
                        for chunk in self.buffer.list_session(
                            session_id,
                            final_only=True,
                        )
                        if chunk.chunk_id == correction.chunk_id
                    ),
                    None,
                )
                if current is None:
                    continue
                if (
                    current.source_text.strip() == correction.source_text
                    and current.translated_text.strip() == correction.translated_text
                ):
                    continue

                next_revision = current.revision + 1
                reasons = [f"千问上下文复核：{correction.reason}"]
                corrected_chunk = TranscriptChunk(
                    chunk_id=current.chunk_id,
                    source_text=correction.source_text,
                    translated_text=correction.translated_text,
                    direct_translation=current.direct_translation or current.translated_text,
                    is_final=True,
                    session_id=session_id,
                    revision=next_revision,
                    auto_correction=True,
                    correction_reasons=reasons,
                )
                self.buffer.upsert(corrected_chunk)
                transcript_store.save_chunk(corrected_chunk)
                revision_manager.record(corrected_chunk, next_revision)
                self._revisions[current.chunk_id] = next_revision
                await self._broadcast_auto_correction(
                    session_id,
                    current.chunk_id,
                    current.revision,
                    next_revision,
                    correction.source_text,
                    correction.translated_text,
                    corrected_chunk.direct_translation,
                    True,
                    reasons,
                )

    def _schedule_context_review(self, session_id: str) -> None:
        task = asyncio.create_task(self._review_context(session_id))
        self._correction_tasks.add(task)
        task.add_done_callback(self._correction_tasks.discard)

    async def handle_asr_result(
        self,
        session_id: str,
        asr_result: ASRResult,
        byte_length: int = 0,
    ) -> None:
        source_text = asr_result.text.strip()
        model_translated_text = (asr_result.translated_text or "").strip()
        if not source_text and not model_translated_text:
            return

        is_final = asr_result.is_final
        chunk_id = self._active_chunk_ids.get(session_id)
        if not chunk_id:
            chunk_id = self._new_chunk_id(session_id)
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
        if source_text and model_translated_text:
            glossary_manager.remember_context(session_id, source_text)
            self._active_chunk_ids.pop(session_id, None)
            translation_source_text = source_text
        elif source_text:
            glossary_manager.remember_context(session_id, source_text)
            buffered_text = self._append_sentence_buffer(session_id, source_text)
            self._active_chunk_ids.pop(session_id, None)
            if buffered_text is None:
                return
            translation_source_text = buffered_text
            chunk_id = self._new_chunk_id(session_id)
            current_revision = 1
            self._revisions[chunk_id] = current_revision
        else:
            translation_source_text = ""

        if model_translated_text:
            translated_text = model_translated_text
        elif translation_source_text:
            translated_text = await self._translate_text(
                session_id,
                translation_source_text,
                asr_result.language,
                model_translated_text,
            )
        else:
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
            direct_translation=event.translated_text,
            is_final=event.is_final,
            session_id=session_id,
            revision=event.revision,
        )
        self.buffer.upsert(chunk_record)
        transcript_store.save_chunk(chunk_record)
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
                    "directTranslation": event.translated_text,
                    "isFinal": event.is_final,
                    "revision": event.revision,
                    "glossaryConversions": chunk_record.glossary_conversions,
                    "byteLength": byte_length,
                    "confidence": asr_result.confidence,
                    "language": asr_result.language,
                },
            },
        )

        corrected_source, corrected_translation, corrected_revision, correction_reasons = await self._auto_correct_final_chunk(
            session_id,
            event.chunk_id,
            event.source_text,
            event.translated_text,
            asr_result,
            event.revision,
        )
        if correction_reasons:
            event.source_text = corrected_source
            event.translated_text = corrected_translation
            event.revision = corrected_revision
            self._revisions[event.chunk_id] = corrected_revision
            if self.tts_provider and corrected_translation:
                await self.tts_provider.speak(corrected_translation, language=self.target_language)
        self._schedule_context_review(session_id)

    async def handle_audio_chunk(self, session_id: str, chunk: bytes) -> None:
        asr_result = await self.asr_provider.transcribe(chunk, session_id)
        await self.handle_asr_result(session_id, asr_result, len(chunk))

    async def close_session(self, session_id: str) -> None:
        self._active_chunk_ids.pop(session_id, None)
        self._sentence_buffers.pop(session_id, None)
        self._sentence_buffer_started_at.pop(session_id, None)
        pending_tasks = list(self._correction_tasks)
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)
        await self.asr_provider.close_session(session_id)
