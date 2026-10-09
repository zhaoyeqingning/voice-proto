"""一轮会话。新的一轮会取消上一轮还没播完的内容。"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from clock import Timing
from pipeline import TurnOutcome, TurnRequest, run_turn
from ports import Asr, Llm, Player, Tts


class Session:
    def __init__(
        self,
        asr: Asr,
        llm: Llm,
        tts: Tts,
        player: Player,
        log_path: Path | None = None,
    ) -> None:
        self.asr = asr
        self.llm = llm
        self.tts = tts
        self.player = player
        self.log_path = log_path
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
        outcome: TurnOutcome | None = None
        cancelled = False
        try:
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
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            self._append_log(generation, cancelled, user_text, outcome, timing)

    def _append_log(
        self,
        generation: int,
        cancelled: bool,
        user_text: str | None,
        outcome: TurnOutcome | None,
        timing: Timing,
    ) -> None:
        if self.log_path is None:
            return
        record = {
            "generation": generation,
            "cancelled": cancelled,
            "user_text": outcome.user_text if outcome is not None else (user_text or ""),
            "spoken_text": outcome.spoken_text if outcome is not None else "",
            "stale_audio_played": outcome.stale_audio_played if outcome is not None else 0,
            **timing.snapshot(),
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


async def _wait(task: asyncio.Task[None]) -> None:
    try:
        await task
    except asyncio.CancelledError:
        return
