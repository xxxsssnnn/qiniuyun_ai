from __future__ import annotations

import asyncio
from contextlib import suppress

from app.services.asr import ASRResult
from app.services.transcription_processor import TranscriptionProcessor


class RealtimePipeline:
    def __init__(
        self,
        processor: TranscriptionProcessor,
        session_id: str,
        audio_queue_size: int = 100,
        result_queue_size: int = 100,
    ) -> None:
        self.processor = processor
        self.session_id = session_id
        self.audio_queue: asyncio.Queue[bytes] = asyncio.Queue(audio_queue_size)
        self.result_queue: asyncio.Queue[tuple[ASRResult, int]] = asyncio.Queue(
            result_queue_size
        )
        self._tasks: list[asyncio.Task[None]] = []
        self._closed = False
        self._last_audio_size = 0

    async def start(self) -> None:
        if self._tasks:
            return
        self._tasks = [
            asyncio.create_task(self._audio_sender(), name=f"audio-{self.session_id}"),
            asyncio.create_task(self._model_consumer(), name=f"model-{self.session_id}"),
            asyncio.create_task(self._subtitle_broadcaster(), name=f"broadcast-{self.session_id}"),
        ]

    async def enqueue_audio(self, chunk: bytes) -> None:
        if not self._closed:
            await self.audio_queue.put(chunk)

    async def _audio_sender(self) -> None:
        while True:
            chunk = await self.audio_queue.get()
            try:
                self._last_audio_size = len(chunk)
                await self.processor.asr_provider.send_audio(
                    chunk,
                    self.session_id,
                )
            finally:
                self.audio_queue.task_done()

    async def _model_consumer(self) -> None:
        while True:
            result = await self.processor.asr_provider.receive_result(
                self.session_id
            )
            await self.result_queue.put((result, self._last_audio_size))

    async def _subtitle_broadcaster(self) -> None:
        while True:
            result, byte_length = await self.result_queue.get()
            try:
                await self.processor.handle_asr_result(
                    self.session_id,
                    result,
                    byte_length,
                )
            finally:
                self.result_queue.task_done()

    async def finish_audio(self) -> None:
        await self.audio_queue.join()
        await self.processor.asr_provider.finish_session(self.session_id)

    async def close(self, drain_timeout: float = 1.5) -> None:
        if self._closed:
            return
        self._closed = True
        await self.finish_audio()
        await asyncio.sleep(0.5)
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(self.result_queue.join(), timeout=drain_timeout)
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()
        await self.processor.close_session(self.session_id)
