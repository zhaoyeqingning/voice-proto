import asyncio
import json

from main import run_demo


def test_cli_prints_total_time(tmp_path, capsys):
    log_path = tmp_path / "turns.jsonl"
    asyncio.run(run_demo(log_path))
    output = capsys.readouterr().out
    record = json.loads(log_path.read_text(encoding="utf-8"))
    assert "听" in output
    assert "想" in output
    assert "说" in output
    assert f"合计 {record['total_ms']} 毫秒" in output
    assert record["cancelled"] is False
    assert record["stale_audio_played"] == 0
