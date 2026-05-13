from __future__ import annotations

from pathlib import Path

from core.profanity_censor_detector import (
    classify_profanity_token,
    detect_profanity_censor_candidates,
)
from models.profanity_censor import (
    CENSOR_ACTION_NONE,
    CENSOR_ACTION_SFX_OVERLAY_CANDIDATE,
    REPLACEMENT_SFX_OPTIONS,
    SEVERITY_MILD,
    SEVERITY_SEVERE,
    TIMING_SOURCE_SEGMENT_FALLBACK,
    TIMING_SOURCE_WORD_TIMESTAMP,
    ProfanityCensorMatch,
    ProfanityCensorResult,
    ProfanityCensorSegmentResult,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE = {
    "mild_terms": ["mildword"],
    "severe_terms": ["severe_token"],
    "default_replacement_sfx": "quack",
}
FORBIDDEN_ACTIONS = {
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
}


def _segment(text: str, words: list[dict] | None = None) -> dict:
    data = {
        "segment_id": "s1",
        "start_seconds": 1.0,
        "end_seconds": 3.0,
        "duration_seconds": 2.0,
        "text": text,
    }
    if words is not None:
        data["words"] = words
    return data


def test_profanity_censor_match_roundtrip() -> None:
    match = ProfanityCensorMatch(
        match_id="m1",
        start_seconds=1.0,
        end_seconds=1.2,
        center_seconds=1.1,
        duration_seconds=0.2,
        text="SEVERE_TOKEN",
        matched_text="SEVERE_TOKEN",
        normalized_match="severe_token",
        severity=SEVERITY_SEVERE,
        category="severe_profanity",
        censor_required=True,
        censor_action=CENSOR_ACTION_SFX_OVERLAY_CANDIDATE,
        replacement_sfx="quack",
        timing_source=TIMING_SOURCE_WORD_TIMESTAMP,
        confidence=0.9,
        source_segment_index=0,
        source_word_index=1,
        metadata={"source": "test"},
    )

    restored = ProfanityCensorMatch.from_dict(match.to_dict())

    assert restored.to_dict() == match.to_dict()


def test_profanity_censor_segment_result_roundtrip() -> None:
    segment = ProfanityCensorSegmentResult(
        segment_id="s1",
        start_seconds=1.0,
        end_seconds=2.0,
        duration_seconds=1.0,
        text="test",
        match_count=1,
        severe_match_count=1,
        censor_required_count=1,
        preferred_replacement_sfx="quack",
        matches=[{"match_id": "m1"}],
    )

    restored = ProfanityCensorSegmentResult.from_dict(segment.to_dict())

    assert restored.to_dict() == segment.to_dict()


def test_profanity_censor_result_roundtrip() -> None:
    match = ProfanityCensorMatch(match_id="m1")
    result = ProfanityCensorResult(
        status="ok",
        matches=[match],
        segment_results=[ProfanityCensorSegmentResult(segment_id="s1")],
        match_count=1,
        recommendation="review_censor_sfx_overlay_candidates",
    )

    restored = ProfanityCensorResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_no_transcript_skips_without_crash() -> None:
    result = detect_profanity_censor_candidates([], profile=PROFILE)

    assert result.status == "skipped_no_transcript_segments"
    assert result.recommendation == "profanity_censor_skipped_no_transcript"


def test_mild_term_does_not_require_censor() -> None:
    result = detect_profanity_censor_candidates(
        [_segment("that was mildword")],
        profile=PROFILE,
    )

    assert result.mild_match_count == 1
    assert result.censor_required_count == 0
    assert result.matches[0].severity == SEVERITY_MILD
    assert result.matches[0].censor_action == CENSOR_ACTION_NONE
    assert result.matches[0].replacement_sfx is None


def test_severe_term_requires_censor_sfx_candidate() -> None:
    result = detect_profanity_censor_candidates(
        [_segment("that was SEVERE_TOKEN")],
        profile=PROFILE,
    )

    assert result.severe_match_count == 1
    assert result.censor_required_count == 1
    assert result.matches[0].severity == SEVERITY_SEVERE
    assert result.matches[0].censor_action == CENSOR_ACTION_SFX_OVERLAY_CANDIDATE
    assert result.matches[0].replacement_sfx in REPLACEMENT_SFX_OPTIONS


def test_word_timestamp_is_used_when_available() -> None:
    result = detect_profanity_censor_candidates(
        [
            _segment(
                "clean SEVERE_TOKEN",
                words=[
                    {"word": "clean", "start_seconds": 1.0, "end_seconds": 1.2},
                    {
                        "word": "SEVERE_TOKEN",
                        "start_seconds": 1.2,
                        "end_seconds": 1.5,
                    },
                ],
            )
        ],
        profile=PROFILE,
    )

    match = result.matches[0]
    assert match.timing_source == TIMING_SOURCE_WORD_TIMESTAMP
    assert match.start_seconds == 1.2
    assert match.end_seconds == 1.5
    assert result.word_level_match_count == 1


def test_segment_fallback_is_used_without_word_time() -> None:
    result = detect_profanity_censor_candidates(
        [
            _segment(
                "clean SEVERE_TOKEN",
                words=[
                    {"word": "clean"},
                    {"word": "SEVERE_TOKEN"},
                ],
            )
        ],
        profile=PROFILE,
    )

    match = result.matches[0]
    assert match.timing_source == TIMING_SOURCE_SEGMENT_FALLBACK
    assert match.start_seconds == 1.0
    assert match.end_seconds == 3.0
    assert result.segment_fallback_match_count == 1


def test_multiple_matches_are_counted_correctly() -> None:
    result = detect_profanity_censor_candidates(
        [_segment("mildword SEVERE_TOKEN mildword")],
        profile=PROFILE,
    )

    assert result.match_count == 3
    assert result.mild_match_count == 2
    assert result.severe_match_count == 1
    assert result.censor_required_count == 1


def test_no_cut_remove_or_delete_actions_are_emitted() -> None:
    result = detect_profanity_censor_candidates(
        [_segment("mildword SEVERE_TOKEN")],
        profile=PROFILE,
    )

    actions = {match.censor_action for match in result.matches}
    assert not actions.intersection(FORBIDDEN_ACTIONS)


def test_classification_profile_override() -> None:
    severe = classify_profanity_token("SEVERE_TOKEN", profile=PROFILE)
    mild = classify_profanity_token("mildword", profile=PROFILE)

    assert severe["severity"] == SEVERITY_SEVERE
    assert mild["severity"] == SEVERITY_MILD


def test_profanity_censor_foundation_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "models/profanity_censor.py",
        "core/profanity_censor_detector.py",
        "tests/test_profanity_censor_foundation_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
