"""一轮会话。新的一轮会取消上一轮还没播完的内容。"""

from __future__ import annotations

import asyncio
import time

from clock import Timing
from pipeline import TurnRequest, run_turn
from ports import Asr, Llm, Player, Tts


class Session:
    def __init__(self, asr: Asr, llm: Llm, tts: Tts, player: Player) -> None:
        self.asr = asr
        self.llm = llm
        self.tts = tts
        self.player = player
        self.generation = 0
        self.history: list[dict[str, str]] = []
        self._task: asyncio.Task[None] | None = None

    async def submit_text(self, text: str) -> None:
        await self._start(user_text=text)

    async def submit_audio(self, audio: bytes) -> None:
        await self._start(audio=audio)

    async def _start(self, user_text: str | None = None, audio: bytes | None = None) -> None:
        self.generation += 1
        generation = self.generation
        previous = self._task
        if previous is not None:
            previous.cancel()
            await _wait(previous)
        await self.player.stop()
        timing = Timing(started_at=time.perf_counter())
        self._task = asyncio.create_task(self._run(generation, user_text, audio, timing))
        try:
            await self._task
        except asyncio.CancelledError:
            if self.generation != generation:
                return
            raise

    async def _run(
        self,
        generation: int,
        user_text: str | None,
        audio: bytes | None,
        timing: Timing,
    ) -> None:
        outcome = await run_turn(
            TurnRequest(generation, list(self.history), user_text, audio),
            asr=self.asr,
            llm=self.llm,
            tts=self.tts,
            player=self.player,
            is_current=lambda: self.generation == generation,
            timing=timing,
        )
        if outcome.spoken_text and self.generation == generation:
            self.history.append({"role": "user", "text": outcome.user_text})
            self.history.append({"role": "assistant", "text": outcome.spoken_text})


async def _wait(task: asyncio.Task[None]) -> None:
    try:
        await task
    except asyncio.CancelledError:
        return
