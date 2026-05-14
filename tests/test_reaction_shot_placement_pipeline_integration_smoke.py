from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "core" / "gaming_pipeline.py"


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_pipeline_imports_reaction_shot_placement_runner() -> None:
    text = _pipeline_text()

    assert "from core.reaction_shot_placement_runner import" in text
    assert "run_reaction_shot_placement_for_job" in text
    assert "store_reaction_shot_placement_run_report_to_job" in text


def test_pipeline_runs_reaction_shot_placement_after_pattern_interrupt() -> None:
    text = _pipeline_text()

    pattern_index = text.index("run_pattern_interrupt_for_job(")
    pattern_apply_index = text.index("store_pattern_interrupt_run_report_to_job(")
    reaction_index = text.index("run_reaction_shot_placement_for_job(")
    reaction_apply_index = text.index(
        "store_reaction_shot_placement_run_report_to_job("
    )

    assert pattern_index < pattern_apply_index < reaction_index < reaction_apply_index


def test_pipeline_reaction_shot_placement_metadata_is_review_only() -> None:
    text = _pipeline_text()
    start = text.index("run_reaction_shot_placement_for_job(")
    block = text[start : start + 1800]

    required_tokens = [
        '"phase": "2B-41"',
        '"block": "block7_story_pacing"',
        '"review_only": True',
        '"reaction_shot_placement_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_41": True',
        '"no_render_in_2b_41": True',
        '"no_timeline_reorder_in_2b_41": True',
        '"no_reaction_apply_in_2b_41": True',
        '"no_reaction_insert_in_2b_41": True',
        '"no_facecam_move_in_2b_41": True',
        '"no_zoom_insert_in_2b_41": True',
    ]

    for token in required_tokens:
        assert token in block


def test_pipeline_reaction_shot_placement_never_allows_execution_flags() -> None:
    text = _pipeline_text()
    start = text.index("run_reaction_shot_placement_for_job(")
    block = text[start : start + 9000]

    required_tokens = [
        '"can_apply_reaction_shots": False',
        '"can_move_clip": False',
        '"can_insert_clip": False',
        '"can_trim": False',
        '"can_extend": False',
        '"can_reorder_timeline": False',
        '"can_render": False',
        'step_name="reaction_shot_placement_engine_done"',
    ]

    for token in required_tokens:
        assert token in block


def test_pipeline_reaction_shot_placement_logs_expected_event_types() -> None:
    text = _pipeline_text()
    start = text.index("reaction_shot_placement_status")
    block = text[start : start + 1800]

    assert "REACTION_SHOT_PLACEMENT_READY" in block
    assert "REACTION_SHOT_PLACEMENT_READY_WITH_WARNINGS" in block
    assert "REACTION_SHOT_PLACEMENT_BLOCKED" in block
    assert "REACTION_SHOT_PLACEMENT_FAILED" in block


def test_pipeline_file_has_no_bom_and_ends_with_newline() -> None:
    content = PIPELINE_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")