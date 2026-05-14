from __future__ import annotations

import importlib.util
from pathlib import Path

from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]


BLOCK7_SOURCES = [
    "hook_identification",
    "emotional_arc",
    "dynamic_pacing",
    "pattern_interrupt",
    "reaction_shot_placement",
    "but_therefore_story",
    "final_quality_validator",
]

EXPECTED_SIGNAL_TYPES = {
    "hook_candidate_found",
    "hook_candidate_review_required",
    "hook_candidate_high_score",
    "emotional_arc_ready_with_warnings",
    "emotional_arc_weak_hook",
    "emotional_arc_missing_climax",
    "dynamic_pacing_ready_with_warnings",
    "dynamic_pacing_good_match",
    "dynamic_pacing_too_slow_for_energy",
    "dynamic_pacing_missing_breathing_room",
    "pattern_interrupt_ready_with_warnings",
    "pattern_interrupt_needed",
    "pattern_interrupt_zoom_reaction_candidate",
    "pattern_interrupt_text_overlay_candidate",
    "reaction_shot_placement_ready_with_warnings",
    "reaction_shot_candidate_found",
    "reaction_shot_after_highlight_candidate",
    "reaction_shot_after_hook_candidate",
    "reaction_shot_after_climax_candidate",
    "reaction_shot_after_pattern_interrupt_candidate",
    "reaction_shot_missing_placeholder",
    "but_therefore_story_ready_with_warnings",
    "story_but_moment",
    "story_therefore_moment",
    "story_and_moment",
    "story_weak_but_therefore_ratio",
    "final_quality_ready_with_warnings",
    "final_quality_story_warning",
    "final_quality_safety_blocked",
}


def _load_test_module(relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook_registry = _load_test_module("tests/test_hook_identification_registry_integration_smoke.py")
emotional_arc_registry = _load_test_module("tests/test_emotional_arc_registry_integration_smoke.py")
dynamic_pacing_registry = _load_test_module("tests/test_dynamic_pacing_registry_integration_smoke.py")
pattern_interrupt_registry = _load_test_module("tests/test_pattern_interrupt_registry_integration_smoke.py")
reaction_shot_registry = _load_test_module("tests/test_reaction_shot_placement_registry_integration_smoke.py")
story_registry = _load_test_module("tests/test_but_therefore_story_registry_integration_smoke.py")
final_quality_registry = _load_test_module("tests/test_final_quality_validator_registry_integration_smoke.py")


def _registry_text() -> str:
    return (ROOT / "core" / "unified_edit_signal_registry.py").read_text(
        encoding="utf-8"
    )


def _block7_job() -> Job:
    payload = hook_registry._job_payload(
        job_id="job_block7_registry_audit",
        hook_identification_report=hook_registry._report(),
        emotional_arc_report=emotional_arc_registry._report(),
        dynamic_pacing_report=dynamic_pacing_registry._report(),
        pattern_interrupt_report=pattern_interrupt_registry._report(),
        reaction_shot_placement_report=reaction_shot_registry._report(),
        but_therefore_story_report=story_registry._story_report(),
        final_quality_validation_report=final_quality_registry._job_with_final_quality_report().final_quality_validation_report,
    )
    return Job.from_dict(payload)


def test_registry_contains_all_block7_sources_in_source_code():
    text = _registry_text()

    missing = [
        source
        for source in BLOCK7_SOURCES
        if source not in text
    ]

    assert missing == []


def test_registry_imports_all_block7_signal_adapters():
    text = _registry_text()

    required_markers = [
        "adapt_hook_identification_report_to_signals",
        "adapt_emotional_arc_report_to_signals",
        "adapt_dynamic_pacing_report_to_signals",
        "adapt_pattern_interrupt_report_to_signals",
        "adapt_reaction_shot_placement_report_to_signals",
        "adapt_but_therefore_story_report_to_signals",
        "build_final_quality_validator_signals",
    ]

    missing = [
        marker
        for marker in required_markers
        if marker not in text
    ]

    assert missing == []


def test_registry_collects_signals_from_all_block7_sources():
    result = run_unified_edit_signal_registry_for_job(_block7_job())

    missing_sources = [
        source
        for source in BLOCK7_SOURCES
        if result.source_counts.get(source, 0) < 1
    ]

    assert missing_sources == []


def test_registry_collects_expected_block7_signal_types():
    result = run_unified_edit_signal_registry_for_job(_block7_job())

    signal_types = {
        signal.get("signal_type")
        for signal in result.signals
    }

    missing = sorted(EXPECTED_SIGNAL_TYPES - signal_types)

    assert missing == []


def test_all_collected_block7_signals_stay_review_only_and_non_rendering():
    result = run_unified_edit_signal_registry_for_job(_block7_job())

    block7_signals = [
        signal
        for signal in result.signals
        if signal.get("source") in BLOCK7_SOURCES
    ]

    assert block7_signals

    for signal in block7_signals:
        metadata = signal.get("metadata", {})
        assert signal.get("action_hint", "").startswith("review")
        assert metadata.get("review_only") is True
        assert metadata.get("media_unchanged") is True
        assert metadata.get("can_render") is not True

        blocked_execution_flags = [
            "can_apply_hook",
            "can_apply_arc",
            "can_apply_pacing",
            "can_apply_interrupts",
            "can_apply_reaction_shots",
            "can_apply_story_changes",
            "can_reorder_timeline",
            "can_trim",
            "can_extend",
            "can_insert_clip",
            "can_insert_zoom",
            "can_insert_text_overlay",
            "can_insert_sfx",
            "can_apply_fixes",
            "can_execute_timeline",
        ]

        for flag in blocked_execution_flags:
            assert metadata.get(flag) is not True
