"""播放器。当前是只记录调用的假实现，声卡留到后面再接。"""

from __future__ import annotations

from typing import Callable

from ports import AudioBuffer


class FakePlayer:
    def __init__(self) -> None:
        self.played: list[AudioBuffer] = []
        self.stop_count = 0

    async def play(self, audio: AudioBuffer, on_started: Callable[[], None]) -> None:
        on_started()
        self.played.append(audio)

    async def stop(self) -> None:
        self.stop_count += 1
