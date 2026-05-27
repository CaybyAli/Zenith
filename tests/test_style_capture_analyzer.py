from __future__ import annotations

from core.style_capture_analyzer import StyleCaptureAnalyzer


def test_style_capture_analyzer_returns_required_fields() -> None:
    result = StyleCaptureAnalyzer().analyze(
        video_duration_seconds=100.0,
        scene_change_boundaries=[2.0, 5.0, 30.0, 80.0],
        voice_intensity_distribution={
            "normal": 70.0,
            "leise_erhoeht": 10.0,
            "schreien": 15.0,
            "bruellen": 5.0,
        },
        facial_expression_distribution={
            "surprise": 6.0,
            "hand_on_mouth": 4.0,
            "mouth_open_yell": 3.0,
            "neutral": 80.0,
        },
        gameplay_ratio={"gameplay_percent": 85.0, "menu_percent": 15.0},
        speaker_distribution={"ali": 60.0, "friend": 20.0, "unknown": 20.0},
        audio_rms_curve=[-30.0, -20.0, -12.0, -35.0],
        hook={"pattern_class": "high_reaction"},
        transcript={"first_10s_text": "Oh mein Gott was passiert hier"},
    )

    assert len(result["cut_density_curve"]) == 10
    assert result["reaction_density"]["voice_peak_count"] > 0
    assert result["audio_dynamic_range"]["range_db"] == 23.0
    assert 0.0 <= result["signature_score"] <= 1.0
    assert result["focus_decision_distribution"]["total_decisions"] == 100


def test_style_capture_focus_distribution_sums_to_approximately_100() -> None:
    result = StyleCaptureAnalyzer().analyze(
        video_duration_seconds=60.0,
        scene_change_boundaries=[10.0, 20.0],
        voice_intensity_distribution={"normal": 100.0},
        facial_expression_distribution={"neutral": 100.0},
        gameplay_ratio={"gameplay_percent": 90.0, "menu_percent": 10.0},
        speaker_distribution={},
        audio_rms_curve=[-20.0] * 20,
        hook={"pattern_class": "narrative"},
        transcript={"first_10s_text": "So meine Freunde willkommen"},
    )

    focus = result["focus_decision_distribution"]
    total = focus["facecam_pct"] + focus["gameplay_pct"] + focus["balanced_pct"] + focus["drop_pct"]
    assert round(total, 1) == 100.0
