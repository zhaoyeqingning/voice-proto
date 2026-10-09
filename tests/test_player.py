import asyncio

from player import FakePlayer
from ports import SAMPLE_RATE, AudioBuffer, silence_pcm


def test_fake_player_records_audio_and_stop():
    async def scenario() -> None:
        player = FakePlayer()
        audio = AudioBuffer(silence_pcm(), SAMPLE_RATE, generation=1, seq=0, text="你好。")
        started: list[int] = []
        await player.play(audio, lambda: started.append(audio.generation))
        await player.stop()
        assert player.played == [audio]
        assert started == [1]
        assert player.stop_count == 1
        assert len(audio.pcm) % 2 == 0
        assert audio.sample_rate == 24000

    asyncio.run(scenario())
