from __future__ import annotations

from pathlib import Path


def test_p2_8_real_whisper_marker_is_registered() -> None:
    source = Path("pytest.ini").read_text(encoding="utf-8")

    assert "real_whisper:" in source
    assert "optional real Whisper/faster-whisper tests" in source


def test_p2_8_real_whisper_fixture_probe_is_skip_safe_not_fail_hard() -> None:
    source = Path("tests/test_transcript_whisper_fixture_probe.py").read_text(encoding="utf-8")

    assert "@pytest.mark.real_whisper" in source
    assert "pytest.skip(" in source
    assert "Real Whisper fixture unavailable in this environment" in source
    assert "pytest.fail(f\"Whisper failed on bundled speech fixture" not in source
    assert "TranscriptUnavailableError" in source



def test_p2_8_pipeline_s2_real_whisper_e2e_is_marked_and_preflight_skip_safe() -> None:
    source = Path("tests/test_pipeline_e2e_scenarios.py").read_text(encoding="utf-8")

    assert "@pytest.mark.real_whisper" in source
    assert "def _skip_if_real_whisper_fixture_unavailable()" in source
    assert "_skip_if_real_whisper_fixture_unavailable()" in source
    assert "Real Whisper fixture unavailable in this environment" in source
    assert "TranscriptUnavailableError" in source
