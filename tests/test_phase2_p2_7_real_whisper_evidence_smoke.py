from __future__ import annotations

import json
from pathlib import Path


EVIDENCE_PATH = Path("reports/phase2/p2_7_real_whisper_evidence.json")


def test_p2_7_real_whisper_evidence_records_non_test_mode_runtime_probe() -> None:
    assert EVIDENCE_PATH.is_file(), "Missing P2-7 real Whisper evidence file"

    data = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    assert data["phase"] == "P2-7"
    assert data["test_mode"] is False

    direct_probe = data["direct_probe"]
    assert direct_probe["transcribe_ok"] is True
    assert direct_probe["engine"] in {"faster-whisper", "whisper"}
    assert direct_probe["segment_count"] >= 1
    assert direct_probe["full_text_length"] > 0
    assert direct_probe["first_segment"]["end"] > direct_probe["first_segment"]["start"]
    assert direct_probe["first_segment"]["has_text"] is True


def test_p2_7_real_whisper_evidence_records_required_pytest_probes() -> None:
    data = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    pytest_info = data["pytest"]

    assert "ZENITH_TRANSCRIPT_TEST_MODE" not in pytest_info["command"]
    assert "test_transcript_whisper_fixture_probe.py" in pytest_info["command"]
    assert "test_s2_pipeline_handles_video_with_whisper_probe_speech" in pytest_info["command"]
    assert pytest_info["result"].startswith("2 passed")
    assert len(pytest_info["tests"]) == 2
