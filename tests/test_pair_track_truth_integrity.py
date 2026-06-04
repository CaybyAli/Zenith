import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRUTH_PATH = ROOT / "video_configs" / "pair_track_truth.json"
PAIR001_CONFIG_PATH = ROOT / "video_configs" / "pair_001.audio_tracks.json"

ROLE_VOCAB = {
    "ali",
    "friend_discord",
    "game",
    "mix",
    "still",
    "discord_plus_game",
}

EXPECTED_SUMMARY = {
    "ali_clean": 20,
    "friend_clean": 7,
    "duos": 15,
    "solos": 5,
    "game_clean": 12,
}


def load_json(path: Path) -> dict:
    assert path.exists(), f"missing file: {path}"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_config_role(track: dict) -> str:
    raw = " ".join(
        str(track.get(key, ""))
        for key in ("role", "audio_track", "speaker")
    ).lower()

    if "silent" in raw or "still" in raw:
        return "still"
    if "owner" in raw or "ali" in raw or "mic" in raw:
        return "ali"
    if "friend" in raw or "discord" in raw:
        return "friend_discord"
    if "game" in raw or "ingame" in raw:
        return "game"

    return "unknown"


def parse_audio_index(value: str) -> str:
    value = str(value).strip()
    prefix = "0:a:"
    assert value.startswith(prefix), f"bad ffmpeg_audio_index: {value}"
    return f"a{value[len(prefix):]}"


def test_pair_track_truth_integrity() -> None:
    truth = load_json(TRUTH_PATH)

    assert truth.get("schema_version") == "p5_g2_5_pair_track_truth_v1", (
        f"bad schema_version: {truth.get('schema_version')}"
    )

    pairs = truth.get("pairs")
    assert isinstance(pairs, dict), "truth['pairs'] must be a dict"

    expected_pair_names = [f"pair_{i:03d}" for i in range(1, 21)]
    assert sorted(pairs.keys()) == expected_pair_names, (
        f"expected pair_001..pair_020, got {sorted(pairs.keys())}"
    )

    computed = {
        "ali_clean": 0,
        "friend_clean": 0,
        "duos": 0,
        "solos": 0,
        "game_clean": 0,
    }

    for pair_name in expected_pair_names:
        pair = pairs[pair_name]

        pair_type = pair.get("pair_type")
        assert pair_type in {"solo", "duo"}, (
            f"{pair_name}: pair_type must be solo/duo, got {pair_type!r}"
        )

        assert pair.get("owner_ear_confirmed") is True, (
            f"{pair_name}: owner_ear_confirmed must be true"
        )

        track_roles = pair.get("track_roles")
        assert isinstance(track_roles, dict) and track_roles, (
            f"{pair_name}: track_roles must be non-empty dict"
        )

        for track_name, role in track_roles.items():
            assert role in ROLE_VOCAB, (
                f"{pair_name} {track_name}: role {role!r} not in vocab {sorted(ROLE_VOCAB)}"
            )

        ali_tracks = [
            track_name
            for track_name, role in track_roles.items()
            if role == "ali"
        ]
        assert len(ali_tracks) == 1, (
            f"{pair_name}: expected exactly one ali track, got {ali_tracks}"
        )

        ali_source = pair.get("ali_source")
        assert ali_source is not None, f"{pair_name}: ali_source must not be null"
        assert ali_source == ali_tracks[0], (
            f"{pair_name}: ali_source {ali_source!r} does not match ali track {ali_tracks[0]!r}"
        )
        assert track_roles[ali_source] == "ali", (
            f"{pair_name}: ali_source role must be ali, got {track_roles[ali_source]!r}"
        )
        assert track_roles[ali_source] != "mix", (
            f"{pair_name}: ali_source must never point to mix"
        )

        friend_tracks = [
            track_name
            for track_name, role in track_roles.items()
            if role == "friend_discord"
        ]
        friend_source = pair.get("friend_source")

        if friend_tracks:
            assert len(friend_tracks) == 1, (
                f"{pair_name}: expected at most one friend_discord track, got {friend_tracks}"
            )
            assert friend_source == friend_tracks[0], (
                f"{pair_name}: friend_source {friend_source!r} must match friend_discord track {friend_tracks[0]!r}"
            )
        else:
            assert friend_source is None, (
                f"{pair_name}: friend_source must be null when no friend_discord track exists"
            )

        game_tracks = [
            track_name
            for track_name, role in track_roles.items()
            if role == "game"
        ]
        game_source = pair.get("game_source")

        if game_tracks:
            assert len(game_tracks) == 1, (
                f"{pair_name}: expected at most one game track, got {game_tracks}"
            )
            assert game_source == game_tracks[0], (
                f"{pair_name}: game_source {game_source!r} must match game track {game_tracks[0]!r}"
            )
        else:
            assert game_source is None, (
                f"{pair_name}: game_source must be null when no clean game track exists"
            )

        discord_plus_game_tracks = [
            track_name
            for track_name, role in track_roles.items()
            if role == "discord_plus_game"
        ]
        for track_name in discord_plus_game_tracks:
            assert friend_source != track_name, (
                f"{pair_name}: discord_plus_game track {track_name} must not be friend_source"
            )
            assert game_source != track_name, (
                f"{pair_name}: discord_plus_game track {track_name} must not be game_source"
            )

        assert pair.get("usable_for_ali_reference") == (ali_source is not None), (
            f"{pair_name}: usable_for_ali_reference mismatch"
        )
        assert pair.get("usable_for_friend_reference") == (friend_source is not None), (
            f"{pair_name}: usable_for_friend_reference mismatch"
        )
        assert pair.get("usable_for_game_audio") == (game_source is not None), (
            f"{pair_name}: usable_for_game_audio mismatch"
        )
        assert pair.get("usable_for_duo_chemistry") == (pair_type == "duo"), (
            f"{pair_name}: usable_for_duo_chemistry mismatch"
        )

        computed["ali_clean"] += int(ali_source is not None)
        computed["friend_clean"] += int(friend_source is not None)
        computed["duos"] += int(pair_type == "duo")
        computed["solos"] += int(pair_type == "solo")
        computed["game_clean"] += int(game_source is not None)

    assert computed == EXPECTED_SUMMARY, (
        f"computed summary mismatch: expected {EXPECTED_SUMMARY}, got {computed}"
    )

    summary = truth.get("summary", {})
    for key, expected_value in EXPECTED_SUMMARY.items():
        assert summary.get(key) == expected_value, (
            f"summary[{key}] expected {expected_value}, got {summary.get(key)}"
        )


def test_pair_001_truth_matches_audio_track_config() -> None:
    truth = load_json(TRUTH_PATH)
    pair_001_truth = truth["pairs"]["pair_001"]["track_roles"]

    config = load_json(PAIR001_CONFIG_PATH)
    config_tracks = {}

    for track in config.get("audio_tracks", []):
        track_key = parse_audio_index(track.get("ffmpeg_audio_index"))
        config_tracks[track_key] = normalize_config_role(track)

    expected = {
        "a0": "ali",
        "a1": "friend_discord",
        "a2": "game",
        "a3": "still",
    }

    assert pair_001_truth == expected, (
        f"pair_001 truth expected {expected}, got {pair_001_truth}"
    )
    assert config_tracks == expected, (
        f"pair_001 config expected {expected}, got {config_tracks}"
    )
    assert pair_001_truth == config_tracks, (
        f"pair_001 truth/config mismatch: truth={pair_001_truth}, config={config_tracks}"
    )

