"""用假的转写、模型和播放器跑一轮，并打印计时。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from player import FakePlayer
from providers.fake import FakeAsr, FakeLlm, FakeTts
from session import Session


async def run_demo(log_path: Path) -> None:
    session = Session(FakeAsr(), FakeLlm(), FakeTts(), FakePlayer(), log_path=log_path)
    await session.submit_text("在吗")
    record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    print(f"听 {record['listen_ms']} 毫秒")
    print(f"想 {record['think_ms']} 毫秒")
    print(f"说 {record['speak_ms']} 毫秒")
    print(f"合计 {record['total_ms']} 毫秒")


def main() -> None:
    asyncio.run(run_demo(Path("runs/turns.jsonl")))


if __name__ == "__main__":
    main()
