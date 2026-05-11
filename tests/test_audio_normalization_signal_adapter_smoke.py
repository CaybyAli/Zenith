from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.audio_normalization_signal_adapter import (
    SOURCE,
    adapt_audio_normalization_plan_to_signals,
    adapt_audio_normalization_run_report_to_signals,
    audio_normalization_plan_to_signal,
    extract_audio_normalization_plan_dict,
)
from models.audio_normalization_signal import AudioNormalizationSignalAdapterResult

try:
    from models.audio_normalization_run import AudioNormalizationRunReport
except Exception:
    AudioNormalizationRunReport = None


REQUIRED_SIGNAL_FIELDS = {
    "signal_type",
    "source",
    "level_status",
    "start_seconds",
    "end_seconds",
    "center_seconds",
    "recommended_gain_db",
    "limited_gain_db",
    "target_rms_dbfs",
    "target_peak_dbfs",
    "normalization_needed",
    "signal_score",
    "priority",
    "reason",
    "source_plan",
    "metadata",
}


def _base_plan(**overrides):
    plan = {
        "level_status": "too_quiet",
        "normalization_needed": True,
        "recommended_gain_db": 4.5,
        "limited_gain_db": 3.0,
        "target_rms_dbfs": -18.0,
        "target_peak_dbfs": -1.0,
        "reason": "Audio is too quiet in the source.",
    }
    plan.update(overrides)
    return plan


def _make_run_report(plan):
    if AudioNormalizationRunReport is not None:
        try:
            return AudioNormalizationRunReport(
                status="ok",
                normalization_result=plan,
                level_status=plan.get("level_status"),
                normalization_needed=plan.get("normalization_needed", False),
                recommendation="use_audio_edit_signals",
                target_rms_dbfs=plan.get("target_rms_dbfs", -18.0),
                target_peak_dbfs=plan.get("target_peak_dbfs", -1.0),
                recommended_gain_db=plan.get("recommended_gain_db", 0.0),
                limited_gain_db=plan.get("limited_gain_db", 0.0),
            )
        except Exception:
            pass

    return SimpleNamespace(normalization_result=plan)


def test_result_roundtrip():
    original = AudioNormalizationSignalAdapterResult(
        status="ok",
        signals=[{"signal_type": "audio_normalization_plan", "signal_score": 0.7}],
        signal_count=1,
        high_priority_signal_count=0,
        signal_types={"audio_normalization_plan": 1},
        max_signal_score=0.7,
        avg_signal_score=0.7,
        warnings=[],
        errors=[],
        recommendation="use_audio_edit_signals",
        metadata={"future_edit_compatible": True},
    )

    restored = AudioNormalizationSignalAdapterResult.from_dict(original.to_dict())

    assert restored.status == "ok"
    assert restored.source == "audio_normalization_signal_adapter"
    assert restored.signal_count == 1
    assert restored.signal_types == {"audio_normalization_plan": 1}
    assert restored.recommendation == "use_audio_edit_signals"


def test_extract_from_dict():
    plan = _base_plan(level_status="too_loud", recommended_gain_db=-2.5)

    extracted = extract_audio_normalization_plan_dict(plan)

    assert extracted is not None
    assert extracted["level_status"] == "too_loud"
    assert extracted["recommended_gain_db"] == -2.5
    assert extracted["normalization_needed"] is True


def test_extract_from_audio_normalization_run_report_object():
    plan = _base_plan(level_status="too_quiet")
    report = _make_run_report(plan)

    extracted = extract_audio_normalization_plan_dict(report)

    assert extracted is not None
    assert extracted["level_status"] == "too_quiet"
    assert extracted["normalization_needed"] is True


def test_extract_from_job_like_object():
    plan = _base_plan(level_status="clipped")
    job_like = SimpleNamespace(audio_normalization_report={"normalization_result": plan})

    extracted = extract_audio_normalization_plan_dict(job_like)

    assert extracted is not None
    assert extracted["level_status"] == "clipped"


def test_too_quiet_to_audio_gain_boost_recommended():
    signal = audio_normalization_plan_to_signal(_base_plan(level_status="too_quiet"))

    assert signal is not None
    assert signal["signal_type"] == "audio_gain_boost_recommended"
    assert signal["priority"] == "high"
    assert signal["signal_score"] == 0.8


def test_too_loud_to_audio_gain_reduce_recommended():
    signal = audio_normalization_plan_to_signal(
        _base_plan(level_status="too_loud", recommended_gain_db=-4.0)
    )

    assert signal is not None
    assert signal["signal_type"] == "audio_gain_reduce_recommended"
    assert signal["priority"] == "high"
    assert signal["signal_score"] == 0.8


def test_clipped_to_audio_clipping_warning():
    signal = audio_normalization_plan_to_signal(_base_plan(level_status="clipped"))

    assert signal is not None
    assert signal["signal_type"] == "audio_clipping_warning"
    assert signal["priority"] == "high"
    assert signal["signal_score"] == 1.0


def test_silent_to_audio_silent_warning():
    signal = audio_normalization_plan_to_signal(_base_plan(level_status="silent"))

    assert signal is not None
    assert signal["signal_type"] == "audio_silent_warning"
    assert signal["priority"] == "high"
    assert signal["signal_score"] == 0.9


def test_normal_no_needed_to_audio_no_normalization_needed():
    signal = audio_normalization_plan_to_signal(
        _base_plan(
            level_status="normal",
            normalization_needed=False,
            recommended_gain_db=0.0,
            limited_gain_db=0.0,
        )
    )

    assert signal is not None
    assert signal["signal_type"] == "audio_no_normalization_needed"
    assert signal["priority"] == "low"
    assert signal["signal_score"] == 0.3


def test_normalization_needed_true_to_audio_normalization_plan():
    signal = audio_normalization_plan_to_signal(
        _base_plan(level_status="normal", normalization_needed=True)
    )

    assert signal is not None
    assert signal["signal_type"] == "audio_normalization_plan"
    assert signal["priority"] == "medium"
    assert signal["signal_score"] == 0.7


def test_signal_priority_high_medium_low():
    high = audio_normalization_plan_to_signal(_base_plan(level_status="too_quiet"))
    medium = audio_normalization_plan_to_signal(
        _base_plan(level_status="normal", normalization_needed=True)
    )
    low = audio_normalization_plan_to_signal(
        _base_plan(level_status="normal", normalization_needed=False)
    )

    assert high is not None
    assert medium is not None
    assert low is not None

    assert high["priority"] == "high"
    assert medium["priority"] == "medium"
    assert low["priority"] == "low"


def test_adapt_plan_to_signals_basic():
    signals = adapt_audio_normalization_plan_to_signals(_base_plan(level_status="too_quiet"))

    signal_types = {signal["signal_type"] for signal in signals}

    assert len(signals) == 2
    assert "audio_gain_boost_recommended" in signal_types
    assert "audio_normalization_plan" in signal_types


def test_adapt_run_report_to_signals():
    report = _make_run_report(_base_plan(level_status="too_loud"))
    result = adapt_audio_normalization_run_report_to_signals(report)

    assert result.status == "ok"
    assert result.recommendation == "use_audio_edit_signals"
    assert result.signal_count == 2
    assert result.high_priority_signal_count == 1
    assert result.signal_types["audio_gain_reduce_recommended"] == 1
    assert result.signal_types["audio_normalization_plan"] == 1


def test_no_plan_safe():
    result = adapt_audio_normalization_run_report_to_signals({"not_audio": "data"})

    assert result.status == "skipped_no_normalization_plan"
    assert result.recommendation == "no_normalization_plan_available"
    assert result.signal_count == 0
    assert result.errors == []
    assert result.warnings


def test_bad_data_safe():
    result = adapt_audio_normalization_run_report_to_signals(
        {
            "normalization_result": {
                "level_status": None,
                "normalization_needed": "maybe",
                "recommended_gain_db": "not-a-number",
                "limited_gain_db": object(),
                "target_rms_dbfs": "bad",
                "target_peak_dbfs": None,
            }
        }
    )

    assert result.status in {"ok", "completed_with_warnings", "skipped_no_normalization_plan", "failed"}
    assert isinstance(result.to_dict(), dict)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)


def test_future_edit_compatible_output_required_fields():
    signal = audio_normalization_plan_to_signal(_base_plan(level_status="clipped"))

    assert signal is not None
    assert REQUIRED_SIGNAL_FIELDS.issubset(signal.keys())

    assert signal["source"] == SOURCE
    assert signal["start_seconds"] is None
    assert signal["end_seconds"] is None
    assert signal["center_seconds"] is None
    assert isinstance(signal["source_plan"], dict)
    assert isinstance(signal["metadata"], dict)
    assert signal["metadata"]["future_edit_compatible"] is True


def test_bom_newline_hygiene():
    current_file = Path(__file__)
    content = current_file.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    
    assert content.endswith(b"\n")
