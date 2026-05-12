from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


JOB_ID = "phase3c_proof_001"
TMP_ROOT = REPO_ROOT / "tmp" / "phase3c_proof"


def _make_job() -> Job:
    return Job(
        job_id=JOB_ID,
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="input.mp4",
    )


def _populate_realistic_reports(job: Job) -> None:
    job.energy_peak_report = {
        "status": "ok",
        "peak_count": 3,
        "peaks": [
            {
                "peak_type": "high_energy",
                "start_seconds": 2.0,
                "end_seconds": 3.0,
                "center_seconds": 2.5,
                "energy_score": 0.92,
                "peak_score": 0.92,
                "confidence": 0.87,
                "reason": "high_energy_burst",
                "rules_applied": ["high_energy"],
            },
            {
                "peak_type": "sudden_rise",
                "start_seconds": 6.4,
                "end_seconds": 7.2,
                "center_seconds": 6.8,
                "energy_score": 0.74,
                "peak_score": 0.74,
                "confidence": 0.72,
                "reason": "rms_rise",
                "rules_applied": ["sudden_rise"],
            },
            {
                "peak_type": "combined",
                "start_seconds": 11.0,
                "end_seconds": 12.0,
                "center_seconds": 11.5,
                "energy_score": 0.95,
                "peak_score": 0.95,
                "confidence": 0.9,
                "reason": "combined_burst",
                "rules_applied": ["high_energy", "sudden_rise"],
            },
        ],
        "recommendation": "use_peaks",
    }

    job.filler_word_report = {
        "status": "ok",
        "occurrence_count": 2,
        "occurrences": [
            {
                "text": "ähm",
                "normalized_text": "ähm",
                "filler_type": "hesitation",
                "language": "de",
                "start_seconds": 4.0,
                "end_seconds": 4.18,
                "center_seconds": 4.09,
                "duration_seconds": 0.18,
                "confidence": 0.75,
                "remove_candidate": True,
                "reason": "hesitation",
            },
            {
                "text": "halt",
                "normalized_text": "halt",
                "filler_type": "discourse_marker",
                "language": "de",
                "start_seconds": 9.0,
                "end_seconds": 9.2,
                "center_seconds": 9.1,
                "duration_seconds": 0.2,
                "confidence": 0.65,
                "remove_candidate": True,
                "reason": "discourse_marker",
            },
        ],
        "recommendation": "use_filler_word_analysis",
        "transcript_source": "job.transcript_segments",
    }

    job.audio_normalization_report = {
        "status": "completed_with_warnings",
        "level_status": "too_quiet",
        "normalization_needed": True,
        "recommended_gain_db": 6.5,
        "limited_gain_db": 6.0,
        "target_rms_dbfs": -18.0,
        "target_peak_dbfs": -1.0,
        "reason": "audio_too_quiet",
    }

    beats = [
        {
            "time_seconds": 0.5,
            "strength": 0.92,
            "confidence": 0.88,
            "is_downbeat_candidate": True,
        },
        {
            "time_seconds": 1.0,
            "strength": 0.7,
            "confidence": 0.7,
            "is_downbeat_candidate": False,
        },
        {
            "time_seconds": 1.05,
            "strength": 0.85,
            "confidence": 0.85,
            "is_downbeat_candidate": False,
        },
        {
            "time_seconds": 2.5,
            "strength": 0.6,
            "confidence": 0.6,
            "is_downbeat_candidate": False,
        },
        {
            "time_seconds": 6.8,
            "strength": 0.55,
            "confidence": 0.55,
            "is_downbeat_candidate": False,
        },
    ]
    job.beat_detection_report = {
        "status": "ok",
        "beat_count": len(beats),
        "estimated_bpm": 124.0,
        "beats": beats,
        "beat_detection_result": {"beats": beats},
        "recommendation": "use_beats",
    }

    job.silence_classifications = [
        {
            "start_seconds": 5.0,
            "end_seconds": 5.8,
            "duration_seconds": 0.8,
            "classification": "silence_remove",
            "remove_candidate": True,
            "confidence": 0.82,
            "reason": "long_silence",
        },
        {
            "start_seconds": 10.0,
            "end_seconds": 10.4,
            "duration_seconds": 0.4,
            "classification": "speech_pause",
            "remove_candidate": False,
            "confidence": 0.7,
            "reason": "short_breath",
        },
    ]


def main() -> int:
    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT)
    TMP_ROOT.mkdir(parents=True, exist_ok=True)

    job = _make_job()
    _populate_realistic_reports(job)

    result = run_unified_edit_signal_registry_for_job(
        job=job,
        metadata={"stage": "3-C", "proof": True},
    )

    job_dump_path = TMP_ROOT / "job.json"
    job_dump_path.write_text(
        json.dumps(job.to_dict(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    signals_preview = [
        {
            "signal_id": s["signal_id"],
            "signal_type": s["signal_type"],
            "source": s["source"],
            "center_seconds": s["center_seconds"],
            "priority": s["priority"],
            "signal_score": s["signal_score"],
            "action_hint": s["action_hint"],
            "duplicate_count": (s.get("metadata") or {}).get("duplicate_count", 0),
        }
        for s in result.signals
    ]

    summary = {
        "job_id": JOB_ID,
        "status": result.status,
        "signal_count": result.signal_count,
        "source_counts": result.source_counts,
        "type_counts": result.type_counts,
        "priority_counts": result.priority_counts,
        "duplicate_count": result.duplicate_count,
        "max_signal_score": result.max_signal_score,
        "avg_signal_score": result.avg_signal_score,
        "timeline_coverage_seconds": result.timeline_coverage_seconds,
        "recommendation": result.recommendation,
        "warnings": list(result.warnings or []),
        "errors": list(result.errors or []),
        "signals_preview": signals_preview,
        "job_unified_edit_signal_status": job.unified_edit_signal_status,
        "job_unified_edit_signal_count": job.unified_edit_signal_count,
        "job_unified_edit_signal_summary": job.unified_edit_signal_summary,
        "job_dump_path": str(job_dump_path),
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
