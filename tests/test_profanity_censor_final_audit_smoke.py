from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from core.profanity_censor_detector import detect_profanity_censor_candidates
from core.profanity_censor_signal_adapter import adapt_profanity_censor_report_to_signals
from models.job import Job


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_FILES = [
    "models/profanity_censor.py",
    "core/profanity_censor_detector.py",
    "models/profanity_censor_run.py",
    "core/profanity_censor_runner.py",
    "core/profanity_censor_signal_adapter.py",
    "assets/sfx/censor/censor_sfx_manifest.json",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]
PROFANITY_CODE_FILES = [
    "models/profanity_censor.py",
    "core/profanity_censor_detector.py",
    "models/profanity_censor_run.py",
    "core/profanity_censor_runner.py",
    "core/profanity_censor_signal_adapter.py",
]
TEST_FILES = [
    "tests/test_profanity_censor_foundation_smoke.py",
    "tests/test_profanity_censor_asset_manifest_smoke.py",
    "tests/test_profanity_censor_runner_smoke.py",
    "tests/test_profanity_censor_pipeline_integration_smoke.py",
    "tests/test_profanity_censor_signal_adapter_smoke.py",
    "tests/test_profanity_censor_registry_integration_smoke.py",
    "tests/test_profanity_censor_final_audit_smoke.py",
]
FORBIDDEN_PRODUCT_STRINGS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_all_2b245_product_files_exist() -> None:
    for relative_path in PRODUCT_FILES[:6]:
        assert _path(relative_path).is_file(), f"Missing 2B-24.5 file: {relative_path}"


def test_all_2b245_tests_exist() -> None:
    for relative_path in TEST_FILES:
        assert _path(relative_path).is_file(), f"Missing 2B-24.5 test: {relative_path}"


def test_job_has_profanity_censor_fields() -> None:
    field_names = {field.name for field in fields(Job)}
    required = {
        "profanity_censor_report",
        "profanity_censor_status",
        "profanity_censor_matches",
        "profanity_censor_segment_results",
        "profanity_censor_match_count",
        "profanity_censor_severe_match_count",
        "profanity_censor_mild_match_count",
        "profanity_censor_required_count",
        "profanity_censor_word_level_match_count",
        "profanity_censor_segment_fallback_match_count",
        "profanity_censor_recommendation",
    }

    assert not (required - field_names)


def test_pipeline_contains_profanity_censor_block() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "PROFANITY_CENSOR_STARTED" in source
    assert "PROFANITY_CENSOR_DONE" in source
    assert "PROFANITY_CENSOR_SKIPPED" in source
    assert "PROFANITY_CENSOR_FAILED" in source
    assert "run_profanity_censor_for_job(" in source
    assert "apply_profanity_censor_run_report_to_job(" in source
    assert 'step_name="profanity_censor_done"' in source


def test_pipeline_position_after_content_value_before_registry() -> None:
    source = _read("core/gaming_pipeline.py")

    content_index = source.index("CONTENT_VALUE_STARTED")
    profanity_index = source.index("PROFANITY_CENSOR_STARTED")
    registry_index = source.index("UNIFIED_EDIT_SIGNALS_STARTED")

    assert content_index < profanity_index < registry_index


def test_registry_imports_and_processes_profanity_censor() -> None:
    source = _read("core/unified_edit_signal_registry.py")

    assert "from core.profanity_censor_signal_adapter import" in source
    assert "adapt_profanity_censor_report_to_signals" in source
    assert 'SOURCE_PROFANITY_CENSOR = "profanity_censor"' in source


def test_safety_rules_hold_for_mild_and_severe_terms() -> None:
    profile = {
        "mild_terms": ["mildword"],
        "severe_terms": ["severe_token"],
        "default_replacement_sfx": "quack",
    }
    mild = detect_profanity_censor_candidates(
        [{"start_seconds": 1.0, "end_seconds": 2.0, "text": "mildword"}],
        profile=profile,
    )
    severe = detect_profanity_censor_candidates(
        [{"start_seconds": 1.0, "end_seconds": 2.0, "text": "SEVERE_TOKEN"}],
        profile=profile,
    )
    signals = adapt_profanity_censor_report_to_signals(severe.to_dict())

    assert mild.censor_required_count == 0
    assert severe.censor_required_count == 1
    assert severe.matches[0].censor_action == "censor_sfx_overlay_candidate"
    assert signals.censor_required_signal_count == 1


def test_product_files_do_not_contain_forbidden_automatic_actions() -> None:
    for relative_path in PRODUCT_FILES:
        source = _read(relative_path)
        forbidden_found = [
            token for token in FORBIDDEN_PRODUCT_STRINGS if token in source
        ]

        assert not forbidden_found, (
            f"Forbidden automatic action strings in {relative_path}: "
            f"{forbidden_found}"
        )


def test_p2_4_audio_overlay_is_rendered_by_final_render_driver_not_profanity_foundation() -> None:
    manifest = _read("assets/sfx/censor/censor_sfx_manifest.json")
    profanity_code = "\n".join(_read(path) for path in PROFANITY_CODE_FILES)

    assert "P2-4: Real WAV assets are committed and used by FinalRenderDriver." in manifest
    assert "Censor SFX is mixed into rendered audio with FFmpeg amix normalize=0." in manifest
    assert "ffmpeg" not in profanity_code.lower()
    assert "audio_mixing" not in profanity_code.lower()
    assert "amix" not in profanity_code.lower()


def test_2b245_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in PRODUCT_FILES + TEST_FILES:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{relative_path} has BOM"
        assert content.endswith(b"\n"), f"{relative_path} must end with newline"
