from __future__ import annotations

from types import SimpleNamespace

from core.controlled_ffmpeg_execution_signal_adapter import (
    build_controlled_ffmpeg_execution_signals,
)
from core.unified_edit_signal_registry import build_unified_edit_signal_result


class _Job:
    pass


def _job_with_report(status: str = "controlled_ffmpeg_execution_dry_run_ready"):
    report = {
        "status": status,
        "dry_run_only": True,
        "smoke_test_only": True,
        "real_execution_requested": False,
        "real_execution_allowed": False,
        "real_execution_performed": False,
        "can_execute_full_render": False,
        "can_render_timeline": False,
        "can_process_user_media": False,
        "can_write_project_output": False,
        "can_spawn_process": False,
        "output_created": False,
        "output_path": None,
        "blocking_reasons": [],
        "warnings": [],
        "metadata": {
            "controlled_ffmpeg_execution_gate": True,
            "default_dry_run": True,
        },
    }
    job = _Job()
    setattr(job, "controlled_ffmpeg_execution_report", report)
    return job


def test_signal_adapter_builds_controlled_ffmpeg_signals():
    signals = build_controlled_ffmpeg_execution_signals(_job_with_report())

    signal_types = {signal["signal_type"] for signal in signals}

    assert "controlled_ffmpeg_execution_dry_run_ready" in signal_types
    assert "controlled_ffmpeg_full_render_still_not_allowed" in signal_types
    assert "controlled_ffmpeg_user_media_still_not_allowed" in signal_types
    assert "controlled_ffmpeg_project_output_still_not_allowed" in signal_types
    assert all(signal["source"] == "controlled_ffmpeg_execution" for signal in signals)


def test_signal_adapter_reports_smoke_output_created():
    job = _job_with_report("controlled_ffmpeg_execution_smoke_succeeded")
    job.controlled_ffmpeg_execution_report["output_created"] = True
    job.controlled_ffmpeg_execution_report["output_path"] = "D:/Temp/smoke/out.mp4"

    signals = build_controlled_ffmpeg_execution_signals(job)
    signal_types = {signal["signal_type"] for signal in signals}

    assert "controlled_ffmpeg_execution_smoke_succeeded" in signal_types
    assert "controlled_ffmpeg_smoke_output_created" in signal_types


def test_registry_collects_controlled_ffmpeg_execution_signals():
    result = build_unified_edit_signal_result(_job_with_report())

    assert "controlled_ffmpeg_execution" in result.source_counts
    assert result.source_counts["controlled_ffmpeg_execution"] >= 1
    assert any(
        signal["source"] == "controlled_ffmpeg_execution"
        for signal in result.signals
    )
