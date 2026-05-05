from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.cut_indicator_builder import CutIndicatorBuilder
from core.facecam_emotion_indicator_builder import FacecamEmotionIndicatorBuilder
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.facecam_reaction_result import FacecamReactionResult, FacecamReactionWindow
from models.gameplay_event_result import GameplayEventResult, GameplayEventWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult


def _facecam() -> FacecamReactionResult:
    reaction = FacecamReactionWindow(
        start_seconds=1.0,
        end_seconds=2.0,
        reaction_score=0.44,
        motion_score=0.22,
        expression_change_score=0.24,
        label="strong_facecam_reaction",
        reason="reaction smoke",
    )
    motion = FacecamReactionWindow(
        start_seconds=4.0,
        end_seconds=5.0,
        reaction_score=0.14,
        motion_score=0.36,
        expression_change_score=0.05,
        label="calm_facecam",
        reason="motion smoke",
    )
    expression = FacecamReactionWindow(
        start_seconds=7.0,
        end_seconds=8.0,
        reaction_score=0.19,
        motion_score=0.12,
        expression_change_score=0.30,
        label="facecam_reaction",
        reason="expression smoke",
    )
    quiet = FacecamReactionWindow(
        start_seconds=10.0,
        end_seconds=11.0,
        reaction_score=0.02,
        motion_score=0.02,
        expression_change_score=0.01,
        label="calm_facecam",
        reason="quiet smoke",
    )
    return FacecamReactionResult(
        windows=[reaction, motion, expression, quiet],
        reaction_windows=[reaction, expression],
        average_reaction_score=0.198,
        max_reaction_score=0.44,
    )


def _audio_roles() -> AudioRoleResult:
    return AudioRoleResult(
        windows=[
            AudioRoleWindow(
                window_id="audio_shout",
                start_seconds=1.2,
                end_seconds=1.8,
                role_type="shout_like_audio",
                score=0.80,
                confidence=0.70,
                reason="shout smoke",
                source_signal_ids=["sig_shout"],
            ),
            AudioRoleWindow(
                window_id="audio_laugh",
                start_seconds=7.1,
                end_seconds=7.7,
                role_type="laugh_like_audio",
                score=0.76,
                confidence=0.70,
                reason="laugh smoke",
                source_signal_ids=["sig_laugh"],
            ),
        ],
        engine="audio-role-indicator-builder-v1",
    )


def _sentences() -> SentenceTimelineResult:
    return SentenceTimelineResult(
        sentences=[
            SentenceItem(
                sentence_id="sentence_hook",
                text="Alter was war das!",
                start_seconds=1.1,
                end_seconds=1.9,
                duration_seconds=0.8,
                score=0.74,
                confidence=0.90,
                sentence_kind="exclamation",
                source_segment_ids=["segment_shock"],
            ),
            SentenceItem(
                sentence_id="sentence_laugh",
                text="haha das war wild",
                start_seconds=7.0,
                end_seconds=8.0,
                duration_seconds=1.0,
                score=0.62,
                confidence=0.88,
                sentence_kind="normal",
                source_segment_ids=["segment_laugh"],
            ),
        ],
        engine="sentence-timeline-builder-v1",
    )


def _gameplay_events() -> GameplayEventResult:
    return GameplayEventResult(
        windows=[
            GameplayEventWindow(
                event_id="gameplay_flash",
                start_seconds=0.9,
                end_seconds=1.6,
                event_type="goal_or_save_like_flash",
                score=0.82,
                confidence=0.62,
                reason="flash smoke",
                source_window_ids=["vision_flash"],
                source_signal_ids=["sig_flash"],
            )
        ],
        engine="gameplay-event-indicator-builder-v1",
    )


def test_empty_inputs_do_not_crash() -> None:
    result = FacecamEmotionIndicatorBuilder().build()

    assert result.windows == []
    assert result.emotion_counts == {}
    assert result.skipped_reason == "no facecam reaction windows"


def test_facecam_emotion_indicator_smoke() -> None:
    result = FacecamEmotionIndicatorBuilder().build(
        facecam_reaction_result=_facecam(),
        audio_role_result=_audio_roles(),
        sentence_timeline_result=_sentences(),
        gameplay_event_result=_gameplay_events(),
        channel_type="gaming_main",
    )

    emotion_counts = result.emotion_counts
    emotion_types = [window.emotion_type for window in result.windows]

    assert emotion_counts["facecam_reaction_spike"] >= 1
    assert emotion_counts["facecam_motion_spike"] >= 1
    assert emotion_counts["expression_change_like"] >= 1
    assert emotion_counts["mouth_open_like"] >= 1
    assert emotion_counts["smile_like"] >= 1
    assert emotion_counts["laugh_like_face"] >= 1
    assert emotion_counts["shock_like"] >= 1
    assert emotion_counts["head_movement_like"] >= 1
    assert emotion_counts["thumbnail_face_candidate"] >= 1
    assert emotion_counts["low_facecam_value"] >= 1

    payload = result.to_dict()
    assert payload["engine"] == FacecamEmotionIndicatorBuilder.engine
    assert payload["emotion_counts"] == emotion_counts
    assert payload["positive_count"] == result.positive_count
    assert payload["negative_count"] == result.negative_count
    assert payload["windows"]

    indicator_result = CutIndicatorBuilder().build(
        facecam_emotion_result=result,
        channel_type="gaming_main",
    )
    indicator_types = [indicator.indicator_type for indicator in indicator_result.indicators]
    assert "facecam_reaction_spike" in indicator_types
    assert "thumbnail_face_candidate" in indicator_types
    assert any(
        indicator.indicator_type == "low_facecam_value" and indicator.polarity == "negative"
        for indicator in indicator_result.indicators
    )
    assert any(
        indicator.source == "facecam_emotion" and indicator.polarity == "positive"
        for indicator in indicator_result.indicators
    )

    print("FACECAM EMOTION INDICATOR SMOKE TEST PASSED")
    print(f"total_windows={len(result.windows)}")
    print(f"emotion_counts={emotion_counts}")
    print(f"facecam_reaction_spike={emotion_counts.get('facecam_reaction_spike', 0)}")
    print(f"facecam_motion_spike={emotion_counts.get('facecam_motion_spike', 0)}")
    print(f"expression_change_like={emotion_counts.get('expression_change_like', 0)}")
    print(f"mouth_open_like={emotion_counts.get('mouth_open_like', 0)}")
    print(f"smile_like={emotion_counts.get('smile_like', 0)}")
    print(f"laugh_like_face={emotion_counts.get('laugh_like_face', 0)}")
    print(f"shock_like={emotion_counts.get('shock_like', 0)}")
    print(f"thumbnail_face_candidate={emotion_counts.get('thumbnail_face_candidate', 0)}")
    print(f"low_facecam_value={emotion_counts.get('low_facecam_value', 0)}")
    print(f"indicator_types={sorted(set(indicator_types))}")
    print(f"emotion_types={sorted(set(emotion_types))}")


if __name__ == "__main__":
    test_empty_inputs_do_not_crash()
    test_facecam_emotion_indicator_smoke()
