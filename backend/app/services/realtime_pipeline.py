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
        audio_queue_size: int = 32,
        result_queue_size: int = 32,
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
            self._create_task(self._audio_sender(), f"audio-{self.session_id}"),
            self._create_task(self._model_consumer(), f"model-{self.session_id}"),
            self._create_task(
                self._subtitle_broadcaster(),
                f"broadcast-{self.session_id}",
            ),
        ]

    def _create_task(self, coroutine, name: str) -> asyncio.Task[None]:
        return asyncio.create_task(
            self._run_guarded(coroutine, name),
            name=name,
        )

    async def _run_guarded(self, coroutine, task_name: str) -> None:
        try:
            await coroutine
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            await self.processor.manager.broadcast(
                self.session_id,
                {
                    "type": "error",
                    "session_id": self.session_id,
                    "payload": {
                        "message": f"{task_name} failed: {exc}",
                    },
                },
            )

    async def enqueue_audio(self, chunk: bytes) -> None:
        if self._closed:
            return
        if self.audio_queue.full():
            with suppress(asyncio.QueueEmpty):
                self.audio_queue.get_nowait()
                self.audio_queue.task_done()
        await self.audio_queue.put(chunk)

    async def _audio_sender(self) -> None:
        while True:
            chunk = await self.audio_queue.get()
            try:
                self._last_audio_size = len(chunk)
                try:
                    await self.processor.asr_provider.send_audio(
                        chunk,
                        self.session_id,
                    )
                except Exception as exc:
                    await self._broadcast_task_error("audio sender", exc)
            finally:
                self.audio_queue.task_done()

    async def _model_consumer(self) -> None:
        while True:
            try:
                result = await self.processor.asr_provider.receive_result(
                    self.session_id
                )
                if self.result_queue.full():
                    with suppress(asyncio.QueueEmpty):
                        self.result_queue.get_nowait()
                        self.result_queue.task_done()
                await self.result_queue.put((result, self._last_audio_size))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self._broadcast_task_error("model consumer", exc)
                await asyncio.sleep(0.2)

    async def _subtitle_broadcaster(self) -> None:
        while True:
            result, byte_length = await self.result_queue.get()
            try:
                try:
                    await self.processor.handle_asr_result(
                        self.session_id,
                        result,
                        byte_length,
                    )
                except Exception as exc:
                    await self._broadcast_task_error(
                        "subtitle broadcaster",
                        exc,
                    )
            finally:
                self.result_queue.task_done()

    async def _broadcast_task_error(
        self,
        task_name: str,
        exc: Exception,
    ) -> None:
        await self.processor.manager.broadcast(
            self.session_id,
            {
                "type": "error",
                "session_id": self.session_id,
                "payload": {
                    "message": f"{task_name} failed: {exc}",
                },
            },
        )

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
