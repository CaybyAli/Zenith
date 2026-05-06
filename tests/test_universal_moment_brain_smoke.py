from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.universal_moment_brain import UniversalMomentBrain
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow


SCORE_FIELDS = (
    "visual_action_score",
    "gameplay_motion_score",
    "scene_change_score",
    "speech_score",
    "primary_speech_score",
    "secondary_speech_score",
    "shout_score",
    "reaction_score",
    "facecam_emotion_score",
    "menu_wait_score",
    "dead_time_score",
    "private_talk_score",
    "tension_score",
    "pre_action_score",
    "peak_score",
    "post_peak_reaction_score",
    "boring_score",
    "cut_risk_score",
    "zoom_risk_score",
    "moment_score",
)


def analyze(**kwargs) -> UniversalMomentResult:
    return UniversalMomentBrain().analyze(**kwargs)


def has_window(result: UniversalMomentResult, predicate) -> bool:
    return any(predicate(window) for window in result.windows)


def assert_scores_clamped(result: UniversalMomentResult) -> None:
    for window in result.windows:
        for field in SCORE_FIELDS:
            value = getattr(window, field)
            assert 0.0 <= value <= 1.0, (window.window_id, field, value)


def assert_windows_sorted_and_valid(result: UniversalMomentResult) -> None:
    previous = -1.0
    for window in result.windows:
        assert window.end_seconds > window.start_seconds
        assert window.start_seconds >= previous
        previous = window.start_seconds


def main() -> None:
    empty = analyze()
    assert empty.total_windows == 0

    derived = analyze(
        transcript_result={
            "segments": [
                {"start_seconds": 0.4, "end_seconds": 2.0, "text": "normal speech", "confidence": 0.8}
            ]
        }
    )
    assert derived.total_windows > 0
    assert derived.windows[-1].end_seconds == 2.0

    speech = analyze(
        duration_seconds=3.0,
        transcript_result={
            "segments": [
                {"start_seconds": 1.0, "end_seconds": 2.0, "text": "we need context here", "confidence": 0.82}
            ]
        },
        sentence_timeline_result={
            "sentences": [
                {
                    "sentence_id": "s1",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "text": "we need context here",
                    "sentence_kind": "normal",
                    "score": 0.55,
                    "confidence": 0.8,
                }
            ]
        },
    )
    assert has_window(speech, lambda w: w.speech_score > 0.45 and w.moment_type == "speech_context")

    private_menu = analyze(
        duration_seconds=2.0,
        transcript_result={
            "segments": [
                {"start_seconds": 0.5, "end_seconds": 1.5, "text": "private lobby talk", "confidence": 0.8}
            ]
        },
        gameplay_state_result={
            "windows": [
                {"window_id": "menu", "start_seconds": 0.0, "end_seconds": 2.0, "state_type": "menu_wait", "score": 0.9}
            ]
        },
    )
    assert has_window(private_menu, lambda w: w.moment_type == "private_menu_talk" and w.menu_private_risk)

    boring_menu = analyze(
        duration_seconds=2.0,
        gameplay_state_result={
            "windows": [
                {"window_id": "menu", "start_seconds": 0.0, "end_seconds": 2.0, "state_type": "menu_wait", "score": 0.9}
            ]
        },
        audio_role_result={
            "windows": [
                {"window_id": "silence", "start_seconds": 0.0, "end_seconds": 2.0, "role_type": "silence_or_dead_air", "score": 0.85}
            ]
        },
    )
    assert has_window(boring_menu, lambda w: w.moment_type == "boring_wait" and w.should_remove)

    peak = analyze(
        duration_seconds=2.5,
        gameplay_event_result={
            "windows": [
                {"event_id": "goal", "start_seconds": 1.0, "end_seconds": 1.4, "event_type": "goal_or_save_like_flash", "score": 0.9}
            ]
        },
    )
    assert has_window(peak, lambda w: w.moment_type == "peak_action" and w.should_keep)

    pre_action = analyze(
        duration_seconds=2.5,
        gameplay_state_result={
            "windows": [
                {
                    "window_id": "pre",
                    "start_seconds": 0.5,
                    "end_seconds": 1.0,
                    "state_type": "possible_pre_action_context",
                    "score": 0.68,
                }
            ]
        },
        gameplay_event_result={
            "windows": [
                {"event_id": "goal", "start_seconds": 1.5, "end_seconds": 1.75, "event_type": "goal_or_save_like_flash", "score": 0.9}
            ]
        },
    )
    assert has_window(
        pre_action,
        lambda w: w.moment_type == "pre_action_tension" and w.needs_pre_context and w.end_seconds <= 1.5,
    )

    post_peak = analyze(
        duration_seconds=2.5,
        gameplay_event_result={
            "windows": [
                {"event_id": "goal", "start_seconds": 1.0, "end_seconds": 1.2, "event_type": "goal_or_save_like_flash", "score": 0.9}
            ]
        },
        audio_role_result={
            "windows": [
                {"window_id": "shout", "start_seconds": 1.3, "end_seconds": 1.8, "role_type": "shout_like_audio", "score": 0.82}
            ]
        },
        facecam_reaction_result={
            "windows": [
                {"start_seconds": 1.3, "end_seconds": 1.8, "label": "strong_facecam_reaction", "reaction_score": 0.8}
            ]
        },
    )
    assert has_window(
        post_peak,
        lambda w: w.moment_type == "post_peak_reaction" and w.needs_post_context and w.start_seconds >= 1.2,
    )

    speech_cut_risk = analyze(
        duration_seconds=2.5,
        sentence_timeline_result={
            "sentences": [
                {
                    "sentence_id": "risk_sentence",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "text": "do not cut this sentence",
                    "sentence_kind": "normal",
                    "score": 0.55,
                    "confidence": 0.8,
                }
            ]
        },
        audio_role_result={
            "windows": [
                {
                    "window_id": "risk",
                    "start_seconds": 0.9,
                    "end_seconds": 1.1,
                    "role_type": "speech_cut_risk_audio",
                    "score": 0.9,
                }
            ]
        },
    )
    assert has_window(speech_cut_risk, lambda w: w.moment_type == "cut_risk" and w.speech_boundary_risk)

    zoom_risk = analyze(
        duration_seconds=2.5,
        facecam_reaction_result={
            "windows": [
                {"start_seconds": 1.0, "end_seconds": 1.5, "label": "strong_facecam_reaction", "reaction_score": 0.85}
            ]
        },
        cut_indicator_result={
            "indicators": [
                {
                    "indicator_id": "zoom",
                    "indicator_type": "zoom_boundary_risk",
                    "start_seconds": 1.0,
                    "end_seconds": 1.5,
                    "score": 0.82,
                    "confidence": 0.8,
                }
            ]
        },
    )
    assert has_window(zoom_risk, lambda w: w.moment_type == "zoom_risk" and w.zoom_boundary_risk)

    bad_window = UniversalMomentWindow(
        window_id="bad",
        start_seconds=2.0,
        end_seconds=1.0,
        visual_action_score=4.0,
        speech_score=-3.0,
        moment_score=8.0,
    )
    assert bad_window.end_seconds > bad_window.start_seconds
    assert bad_window.visual_action_score == 1.0
    assert bad_window.speech_score == 0.0
    assert bad_window.moment_score == 1.0

    roundtrip = UniversalMomentResult.from_dict(UniversalMomentResult(windows=[bad_window]).to_dict())
    assert roundtrip.total_windows == 1

    for result in [
        empty,
        derived,
        speech,
        private_menu,
        boring_menu,
        peak,
        pre_action,
        post_peak,
        speech_cut_risk,
        zoom_risk,
        roundtrip,
    ]:
        assert_scores_clamped(result)
        assert_windows_sorted_and_valid(result)

    print("UNIVERSAL MOMENT BRAIN SMOKE TEST PASSED")


def test_universal_moment_brain_smoke() -> None:
    main()


if __name__ == "__main__":
    main()
