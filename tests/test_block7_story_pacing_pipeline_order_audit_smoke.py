from __future__ import annotations

import re
from pathlib import Path


PIPELINE_PATH = Path("core/gaming_pipeline.py")


ORDERED_PIPELINE_CALLS = [
    ("2B-37 Hook Identification", r"\bhook_identification_report\s*=\s*run_hook_identification_for_job\s*\("),
    ("2B-38 Emotional Arc", r"\bemotional_arc_report\s*=\s*run_emotional_arc_builder_for_job\s*\("),
    ("2B-39 Dynamic Pacing", r"\bdynamic_pacing_report\s*=\s*run_dynamic_pacing_for_job\s*\("),
    ("2B-40 Pattern Interrupt", r"\bpattern_interrupt_report\s*=\s*run_pattern_interrupt_for_job\s*\("),
    ("2B-41 Reaction Shot Placement", r"\breaction_shot_placement_report\s*=\s*run_reaction_shot_placement_for_job\s*\("),
    ("2B-42 But Therefore Story", r"\bbut_therefore_story_report\s*=\s*run_but_therefore_story_for_job\s*\("),
    ("2B-43 Final Quality Validator", r"\bfinal_quality_report\s*=\s*run_final_quality_validator\s*\("),
]


PIPELINE_METADATA_MARKERS = [
    "block7_story_pacing",
    "review_only",
    "media_unchanged",
    "no_execution_in_2b_37",
    "no_execution_in_2b_38",
    "no_execution_in_2b_39",
    "no_execution_in_2b_40",
    "no_execution_in_2b_41",
    "no_execution_in_2b_42",
    "no_execution_in_2b_43",
    "no_render_in_2b_37",
    "no_render_in_2b_38",
    "no_render_in_2b_39",
    "no_render_in_2b_40",
    "no_render_in_2b_41",
    "no_render_in_2b_42",
    "no_render_in_2b_43",
]


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def _first_match_position(text: str, pattern: str) -> int:
    match = re.search(pattern, text)
    assert match is not None, f"Pipeline call missing: {pattern}"
    return match.start()


def test_block7_pipeline_runs_story_pacing_modules_in_safe_order():
    text = _pipeline_text()

    positions = [
        (label, _first_match_position(text, pattern))
        for label, pattern in ORDERED_PIPELINE_CALLS
    ]

    only_positions = [position for _, position in positions]
    assert only_positions == sorted(only_positions), positions


def test_block7_pipeline_does_not_run_later_modules_before_required_inputs():
    text = _pipeline_text()

    positions = {
        label: _first_match_position(text, pattern)
        for label, pattern in ORDERED_PIPELINE_CALLS
    }

    assert positions["2B-38 Emotional Arc"] > positions["2B-37 Hook Identification"]
    assert positions["2B-39 Dynamic Pacing"] > positions["2B-38 Emotional Arc"]
    assert positions["2B-40 Pattern Interrupt"] > positions["2B-39 Dynamic Pacing"]
    assert positions["2B-41 Reaction Shot Placement"] > positions["2B-40 Pattern Interrupt"]
    assert positions["2B-42 But Therefore Story"] > positions["2B-41 Reaction Shot Placement"]
    assert positions["2B-43 Final Quality Validator"] > positions["2B-42 But Therefore Story"]


def test_block7_pipeline_contains_review_only_safety_metadata_for_each_stage():
    text = _pipeline_text()

    missing = [
        marker
        for marker in PIPELINE_METADATA_MARKERS
        if marker not in text
    ]

    assert missing == []


def test_block7_pipeline_final_quality_runs_after_story_engine_done_checkpoint():
    text = _pipeline_text()

    story_done = text.find('step_name="but_therefore_story_engine_done"')
    final_started = text.find('event_type="FINAL_QUALITY_VALIDATOR_STARTED"')
    final_call = _first_match_position(text, r"\bfinal_quality_report\s*=\s*run_final_quality_validator\s*\(")

    assert story_done != -1
    assert final_started != -1
    assert story_done < final_started < final_call


def test_block7_pipeline_uses_real_current_runner_names():
    text = _pipeline_text()

    assert "run_emotional_arc_builder_for_job" in text
    assert "run_final_quality_validator(job)" in text

    # Alte Wunsch-Namen dürfen nicht als Pflichtnamen vorausgesetzt werden.
    # Wichtig ist: Die echte Codebasis nutzt diese aktuellen Runner-Namen.
    assert "run_emotional_arc_for_job(" not in text
    assert "run_final_quality_validator_for_job(" not in text
