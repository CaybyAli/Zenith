import json
from pathlib import Path

import pytest

from core.style_dna_pacing_adapter import StyleDnaPacingAdapter


def _write_style_dna(path: Path, *, cuts: float) -> None:
    payload = {
        "content_type": "gaming_pairs",
        "source_count": 1,
        "cuts_per_minute": {"median": cuts},
        "median_clip_seconds": {"median": 5.0},
        "audio_dynamic_range": {"median": 12.0},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_real_gaming_style_dna_loads_pacing_decision() -> None:
    decision = StyleDnaPacingAdapter().load_decision()

    assert decision.loaded is True
    assert decision.content_type == "gaming_pairs"
    assert decision.source_count == 20
    assert decision.target_clip_seconds == pytest.approx(5.542, abs=0.01)
    assert decision.cuts_per_minute_median == pytest.approx(5.829, abs=0.01)
    assert decision.audio_dynamic_range_median == pytest.approx(16.63, abs=0.05)
    assert decision.pacing_profile == "balanced"
    assert decision.confidence == 1.0


def test_missing_file_falls_back_without_crash(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing_style_dna.json"

    decision = StyleDnaPacingAdapter().load_decision(missing_path)

    assert decision.loaded is False
    assert decision.pacing_profile == "unknown"
    assert decision.confidence == 0.0
    assert decision.target_clip_seconds is None


def test_invalid_json_falls_back_without_crash(tmp_path: Path) -> None:
    broken_path = tmp_path / "broken_style_dna.json"
    broken_path.write_text("{not valid json", encoding="utf-8")

    decision = StyleDnaPacingAdapter().load_decision(broken_path)

    assert decision.loaded is False
    assert decision.pacing_profile == "unknown"
    assert decision.confidence == 0.0


def test_fast_profile_from_high_cuts_per_minute(tmp_path: Path) -> None:
    style_path = tmp_path / "fast_style_dna.json"
    _write_style_dna(style_path, cuts=9.0)

    decision = StyleDnaPacingAdapter().load_decision(style_path)

    assert decision.loaded is True
    assert decision.pacing_profile == "fast"
    assert decision.confidence == 1.0


def test_slow_profile_from_low_cuts_per_minute(tmp_path: Path) -> None:
    style_path = tmp_path / "slow_style_dna.json"
    _write_style_dna(style_path, cuts=3.0)

    decision = StyleDnaPacingAdapter().load_decision(style_path)

    assert decision.loaded is True
    assert decision.pacing_profile == "slow"
    assert decision.confidence == 1.0