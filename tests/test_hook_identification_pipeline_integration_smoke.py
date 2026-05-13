from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "core" / "gaming_pipeline.py"


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_pipeline_imports_hook_identification_runner() -> None:
    text = _pipeline_text()

    assert "from core.hook_identification_runner import" in text
    assert "run_hook_identification_for_job" in text
    assert "apply_hook_identification_run_report_to_job" in text


def test_pipeline_runs_hook_identification_after_dashboard_package() -> None:
    text = _pipeline_text()

    dashboard_index = text.index("run_review_timeline_dashboard_package_for_job(")
    dashboard_apply_index = text.index(
        "apply_review_timeline_dashboard_package_run_report_to_job("
    )
    hook_index = text.index("run_hook_identification_for_job(")
    hook_apply_index = text.index("apply_hook_identification_run_report_to_job(")

    assert dashboard_index < dashboard_apply_index < hook_index < hook_apply_index


def test_pipeline_hook_identification_metadata_is_review_only() -> None:
    text = _pipeline_text()
    start = text.index("run_hook_identification_for_job(")
    block = text[start : start + 1400]

    required_tokens = [
        '"phase": "2B-37"',
        '"block": "block7_story_pacing"',
        '"review_only": True',
        '"hook_identification_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_37": True',
        '"no_render_in_2b_37": True',
        '"no_timeline_reorder_in_2b_37": True',
    ]

    for token in required_tokens:
        assert token in block


def test_pipeline_hook_identification_never_allows_execution_flags() -> None:
    text = _pipeline_text()
    start = text.index("HOOK_IDENTIFICATION_STARTED")
    end = text.index("timeline_safety_validation_status", start)
    block = text[start:end]

    assert '"can_apply_hook": False' in block
    assert '"can_reorder_timeline": False' in block
    assert '"can_render": False' in block
    assert 'step_name="hook_identification_done"' in block


def test_pipeline_hook_identification_file_has_no_bom_and_ends_with_newline() -> None:
    content = PIPELINE_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
