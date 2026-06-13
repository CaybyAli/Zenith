from core.voice_intensity_analyzer import VoiceIntensity, VoiceIntensityPoint
from core.friend_reaction_beats import FriendReactionBeatConfig, build
from models.transcript_result import TranscriptSegment


def _voice(
    timestamp: float,
    intensity: VoiceIntensity,
    speaker: str,
    rms_dbfs: float = -7.0,
) -> VoiceIntensityPoint:
    return VoiceIntensityPoint(
        timestamp=timestamp,
        intensity=intensity,
        lufs=rms_dbfs - 5.0,
        rms_dbfs=rms_dbfs,
        speaker=speaker,
    )


def test_build_ignores_friend_reaction_keyword_without_loud_or_call_pause() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "ich mache den call", speaker="ali"),
            TranscriptSegment(1.2, 2.0, "boah krass", speaker="friend"),
        ]
    )

    assert beats == []


def test_build_tags_keyword_beat_with_excited_owner_call_pause() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "warte kurz", speaker="ali"),
            TranscriptSegment(1.8, 2.4, "krass ich bin da", speaker="friend"),
        ],
        ali_intensity_points=[_voice(0.2, VoiceIntensity.LEISE_ERHOEHT, "ali")],
    )

    call_pause_beats = [
        beat
        for beat in beats
        if "owner_call_pause" in (beat.evidence.get("tags") or [])
    ]

    assert len(call_pause_beats) == 1
    assert call_pause_beats[0].beat_type == "owner_call_pause"
    assert call_pause_beats[0].start == 1.8
    assert call_pause_beats[0].end == 2.4
    assert call_pause_beats[0].ali_context_text == "warte kurz"
    assert call_pause_beats[0].friend_text == "krass ich bin da"
    assert call_pause_beats[0].evidence["keyword"] == "krass"
    assert call_pause_beats[0].evidence["gap_seconds"] == 0.8


def test_build_respects_configured_call_pause_window() -> None:
    segments = [
        TranscriptSegment(0.0, 1.0, "warte kurz", speaker="ali"),
        TranscriptSegment(1.7, 2.4, "krass ich bin da", speaker="friend"),
    ]

    beats = build(
        segments,
        config=FriendReactionBeatConfig(
            min_call_pause_seconds=0.1,
            max_call_pause_seconds=0.4,
        ),
    )

    assert beats == []


def test_build_ignores_call_pause_without_excited_owner() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "warte kurz", speaker="ali"),
            TranscriptSegment(1.8, 2.4, "ich bin da", speaker="friend"),
        ]
    )

    assert beats == []


def test_build_rejects_friend_segment_longer_than_max_beat_duration_all_types() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "warte kurz", speaker="ali"),
            TranscriptSegment(1.2, 6.0, "krass ich bin da", speaker="friend"),
        ],
        ali_intensity_points=[_voice(0.2, VoiceIntensity.SCHREIEN, "ali")],
        friend_intensity_points=[
            _voice(1.4, VoiceIntensity.SCHREIEN, "friend", rms_dbfs=-5.0)
        ],
        config=FriendReactionBeatConfig(max_beat_duration_seconds=4.0),
    )

    assert beats == []


def test_build_detects_friend_loud_reaction_without_keyword() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "ich mache den call", speaker="ali"),
            TranscriptSegment(1.2, 2.0, "ich bin da", speaker="friend"),
        ],
        friend_intensity_points=[_voice(1.4, VoiceIntensity.SCHREIEN, "friend")],
    )

    assert [beat.beat_type for beat in beats] == ["friend_loud_reaction"]
    assert beats[0].evidence["trigger"] == "friend_voice_intensity"
    assert beats[0].evidence["max_friend_intensity"] == "schreien"
    assert beats[0].friend_text == "ich bin da"


def test_build_friend_loud_requires_upper_friend_rms_percentile() -> None:
    beats = build(
        [
            TranscriptSegment(10.0, 10.6, "ich rede normal", speaker="friend"),
            TranscriptSegment(20.0, 20.6, "ich bin laut", speaker="friend"),
        ],
        friend_intensity_points=[
            _voice(0.0, VoiceIntensity.NORMAL, "friend", rms_dbfs=-30.0),
            _voice(1.0, VoiceIntensity.NORMAL, "friend", rms_dbfs=-29.0),
            _voice(2.0, VoiceIntensity.NORMAL, "friend", rms_dbfs=-28.0),
            _voice(3.0, VoiceIntensity.NORMAL, "friend", rms_dbfs=-27.0),
            _voice(4.0, VoiceIntensity.NORMAL, "friend", rms_dbfs=-26.0),
            _voice(5.0, VoiceIntensity.NORMAL, "friend", rms_dbfs=-25.0),
            _voice(6.0, VoiceIntensity.NORMAL, "friend", rms_dbfs=-24.0),
            _voice(7.0, VoiceIntensity.NORMAL, "friend", rms_dbfs=-23.0),
            _voice(10.1, VoiceIntensity.SCHREIEN, "friend", rms_dbfs=-22.0),
            _voice(20.1, VoiceIntensity.SCHREIEN, "friend", rms_dbfs=-5.0),
        ],
        config=FriendReactionBeatConfig(friend_loud_rms_percentile=90.0),
    )

    assert [beat.beat_type for beat in beats] == ["friend_loud_reaction"]
    assert beats[0].friend_text == "ich bin laut"
    assert beats[0].evidence["friend_loud_rms_dbfs_threshold"] == -20.3


def test_build_prioritizes_loud_over_keyword() -> None:
    beats = build(
        [
            TranscriptSegment(1.2, 2.0, "krass ich bin da", speaker="friend"),
        ],
        friend_intensity_points=[_voice(1.4, VoiceIntensity.BRUELLEN, "friend")],
    )

    assert [beat.beat_type for beat in beats] == ["friend_loud_reaction"]
    assert beats[0].evidence["keyword"] == "krass"
    assert beats[0].evidence["max_friend_intensity"] == "bruellen"


def test_build_detects_owner_call_pause_for_excited_owner_without_friend_keyword() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "gegner kommen", speaker="ali"),
            TranscriptSegment(1.7, 2.1, "wo", speaker="friend"),
        ],
        ali_intensity_points=[_voice(0.1, VoiceIntensity.SCHREIEN, "ali")],
    )

    assert [beat.beat_type for beat in beats] == ["owner_call_pause"]
    assert beats[0].ali_context_text == "gegner kommen"
    assert beats[0].friend_text == "wo"
    assert beats[0].evidence["trigger"] == "ali_voice_intensity_call_pause"
    assert "owner_call_pause" in beats[0].evidence["tags"]


def test_build_rejects_owner_call_pause_when_owner_is_not_excited() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "gegner kommen", speaker="ali"),
            TranscriptSegment(1.7, 2.1, "wo", speaker="friend"),
        ],
        ali_intensity_points=[_voice(0.1, VoiceIntensity.NORMAL, "ali")],
    )

    assert beats == []


def test_build_requires_true_silence_gap_for_call_pause_tag() -> None:
    beats = build(
        [
            TranscriptSegment(0.0, 1.0, "warte kurz", speaker="ali"),
            TranscriptSegment(1.3, 1.5, "noch ein satz", speaker="ali"),
            TranscriptSegment(1.8, 2.4, "krass ich bin da", speaker="friend"),
        ]
    )

    assert beats == []
