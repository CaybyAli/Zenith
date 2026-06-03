from core.audio_track_mapping_config import load_audio_track_mapping_config


def test_pair001_audio_track_mapping_is_config_driven() -> None:
    config = load_audio_track_mapping_config("learning_corpus/pairs/pair_001/raw.mp4")

    assert config is not None
    assert config.video_id == "pair_001"

    mic = config.track_for_audio_track("mic")
    discord = config.track_for_audio_track("discord")
    ingame = config.track_for_audio_track("ingame")
    silent = config.track_for_audio_track("silent")

    assert mic is not None
    assert mic.role == "owner"
    assert mic.speaker == "ali"
    assert mic.ffmpeg_audio_index == 0
    assert mic.transcribe_for_captions is True

    assert discord is not None
    assert discord.role == "friend"
    assert discord.speaker == "friend"
    assert discord.ffmpeg_audio_index == 1
    assert discord.transcribe_for_captions is True

    assert ingame is not None
    assert ingame.transcribe_for_captions is False
    assert silent is not None
    assert silent.transcribe_for_captions is False

    assert [track.audio_track for track in config.caption_tracks()] == ["mic", "discord"]


def test_missing_audio_track_mapping_returns_none(tmp_path) -> None:
    assert load_audio_track_mapping_config(
        "some/unknown/raw.mp4",
        config_dir=tmp_path,
    ) is None
