from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_imports_but_therefore_runner_after_reaction_shot_runner() -> None:
    text = (ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    reaction_import_index = text.index("from core.reaction_shot_placement_runner import")
    story_import_index = text.index("from core.but_therefore_story_runner import")

    assert reaction_import_index < story_import_index
    assert "run_but_therefore_story_for_job" in text
    assert "store_but_therefore_story_run_report_to_job" in text


def test_pipeline_runs_but_therefore_after_reaction_shot_placement() -> None:
    text = (ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    reaction_done_index = text.index("reaction_shot_placement_engine_done")
    story_run_index = text.index("but_therefore_story_report = run_but_therefore_story_for_job")
    story_store_index = text.index("store_but_therefore_story_run_report_to_job", story_run_index)
    story_done_index = text.index("but_therefore_story_engine_done")

    assert reaction_done_index < story_run_index < story_store_index < story_done_index


def test_pipeline_marks_but_therefore_as_review_only_and_no_media_execution() -> None:
    text = (ROOT / "core" / "gaming_pipeline.py").read_text(encoding="utf-8")

    required_tokens = [
        '"phase": "2B-42"',
        '"block": "block7_story_pacing"',
        '"review_only": True',
        '"but_therefore_story_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_42": True',
        '"no_render_in_2b_42": True',
        '"no_timeline_reorder_in_2b_42": True',
        '"no_story_apply_in_2b_42": True',
        '"no_and_moment_remove_in_2b_42": True',
        '"can_apply_story_changes": False',
        '"can_remove_and_moments": False',
        '"can_reorder_timeline": False',
        '"can_trim": False',
        '"can_extend": False',
        '"can_render": False',
        'action="but_therefore_story_review_only"',
    ]

    for token in required_tokens:
        assert token in text
