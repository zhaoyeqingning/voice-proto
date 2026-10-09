from clock import Timing


def test_snapshot_splits_listen_think_speak():
    timing = Timing(
        started_at=0,
        asr_done_at=0.1,
        first_chunk_at=0.3,
        audio_ready_at=0.45,
        playback_started_at=0.5,
    )
    assert timing.snapshot() == {
        "listen_ms": 100,
        "think_ms": 200,
        "speak_ms": 200,
        "audio_ready_ms": 450,
        "total_ms": 500,
    }


def test_missing_playback_leaves_total_empty():
    assert Timing(started_at=1).snapshot()["total_ms"] is None
