"""一轮对话的计时。时间点都用同一块单调时钟。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Timing:
    started_at: float
    asr_done_at: float | None = None
    first_chunk_at: float | None = None
    audio_ready_at: float | None = None
    playback_started_at: float | None = None

    def snapshot(self) -> dict[str, float | None]:
        return {
            "listen_ms": _milliseconds(self.asr_done_at, self.started_at),
            "think_ms": _milliseconds(self.first_chunk_at, self.asr_done_at),
            "speak_ms": _milliseconds(self.playback_started_at, self.first_chunk_at),
            "audio_ready_ms": _milliseconds(self.audio_ready_at, self.started_at),
            "total_ms": _milliseconds(self.playback_started_at, self.started_at),
        }


def _milliseconds(end: float | None, start: float | None) -> float | None:
    if end is None or start is None:
        return None
    return round((end - start) * 1000, 3)
