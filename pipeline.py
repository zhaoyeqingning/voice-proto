"""一轮对话：转写、切段、合成和播放重叠进行。"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from chunker import Chunker
from clock import Timing
from ports import SAMPLE_RATE, Asr, AudioBuffer, Llm, Player, Tts


@dataclass
class TurnRequest:
    generation: int
    history: list[dict[str, str]]
    user_text: str | None = None
    audio: bytes | None = None


@dataclass
class TurnOutcome:
    user_text: str
    spoken_text: str
    timing: Timing
    stale_audio_played: int = 0
    played_generations: list[int] = field(default_factory=list)


async def run_turn(
    request: TurnRequest,
    *,
    asr: Asr,
    llm: Llm,
    tts: Tts,
    player: Player,
    is_current: Callable[[], bool],
    timing: Timing | None = None,
) -> TurnOutcome:
    timing = timing or Timing(started_at=time.perf_counter())
    spoken: list[str] = []
    played_generations: list[int] = []
    user_text = request.user_text or ""
    stale_audio_played = 0
    speak_q: asyncio.Queue[str | None] = asyncio.Queue(maxsize=2)
    audio_q: asyncio.Queue[AudioBuffer | None] = asyncio.Queue(maxsize=2)

    async def produce() -> None:
        nonlocal user_text
        try:
            if request.audio is not None:
                user_text = await asr.transcribe(request.audio)
            timing.asr_done_at = time.perf_counter()
            if not is_current():
                return
            chunker = Chunker()
            async for delta in llm.stream(list(request.history), user_text):
                if not is_current():
                    return
                for piece in chunker.push(delta):
                    if timing.first_chunk_at is None:
                        timing.first_chunk_at = time.perf_counter()
                    await speak_q.put(piece)
            if is_current():
                for piece in chunker.finish():
                    if timing.first_chunk_at is None:
                        timing.first_chunk_at = time.perf_counter()
                    await speak_q.put(piece)
        finally:
            await speak_q.put(None)

    async def synthesize() -> None:
        seq = 0
        try:
            while True:
                piece = await speak_q.get()
                if piece is None or not is_current():
                    return
                pcm = await tts.synthesize(piece)
                if not is_current():
                    return
                if timing.audio_ready_at is None:
                    timing.audio_ready_at = time.perf_counter()
                await audio_q.put(
                    AudioBuffer(pcm, SAMPLE_RATE, request.generation, seq, piece)
                )
                seq += 1
        finally:
            await audio_q.put(None)

    async def play() -> None:
        nonlocal stale_audio_played
        while True:
            audio = await audio_q.get()
            if audio is None:
                return
            if audio.generation != request.generation or not is_current():
                continue
            def started() -> None:
                if timing.playback_started_at is None:
                    timing.playback_started_at = time.perf_counter()

            await player.play(audio, started)
            if audio.generation != request.generation or not is_current():
                stale_audio_played += 1
                continue
            spoken.append(audio.text)
            played_generations.append(audio.generation)

    async with asyncio.TaskGroup() as group:
        group.create_task(produce())
        group.create_task(synthesize())
        group.create_task(play())

    return TurnOutcome(
        user_text=user_text,
        spoken_text="".join(spoken),
        timing=timing,
        stale_audio_played=stale_audio_played,
        played_generations=played_generations,
    )
