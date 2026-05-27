from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.style_capture_analyzer import StyleCaptureAnalyzer
from scripts.p4_7_6_style_capture_extension import STYLE_CAPTURE_REQUIRED_FIELDS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_001 = PROJECT_ROOT / "learning_corpus" / "pairs" / "pair_001" / "style_fingerprint.json"


def test_style_capture_analyzer_accepts_pair_001_fingerprint_data() -> None:
    if not PAIR_001.exists():
        pytest.skip("pair_001 fingerprint not available")

    data = json.loads(PAIR_001.read_text(encoding="utf-8"))
    result = StyleCaptureAnalyzer().analyze(
        video_duration_seconds=1475.77,
        scene_change_boundaries=data["scene_changes"]["boundaries_seconds"],
        voice_intensity_distribution=data["voice_intensity_distribution"],
        facial_expression_distribution=data["facial_expression_distribution"],
        gameplay_ratio=data["gameplay_ratio"],
        speaker_distribution=data.get("speaker_distribution", {}),
        audio_rms_curve=data["audio"]["rms_curve_sampled"],
        hook=data["hook"],
        transcript=data["transcript"],
    )

    assert STYLE_CAPTURE_REQUIRED_FIELDS <= set(result)
    assert len(result["cut_density_curve"]) >= 10
    assert result["focus_decision_distribution"]["total_decisions"] > 0
