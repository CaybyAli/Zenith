from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "transition_decision.py",
    ROOT / "core" / "transition_decision_engine.py",
    ROOT / "models" / "transition_decision_run.py",
    ROOT / "core" / "transition_decision_runner.py",
    ROOT / "core" / "transition_decision_signal_adapter.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_transition_decision_foundation_smoke.py",
    ROOT / "tests" / "test_transition_decision_runner_smoke.py",
    ROOT / "tests" / "test_transition_decision_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_transition_decision_signal_adapter_smoke.py",
    ROOT / "tests" / "test_transition_decision_registry_integration_smoke.py",
    ROOT / "tests" / "test_transition_decision_final_audit_smoke.py",
]

PIPELINE_FILE = ROOT / "core" / "gaming_pipeline.py"
REGISTRY_FILE = ROOT / "core" / "unified_edit_signal_registry.py"
JOB_FILE = ROOT / "models" / "job.py"

FORBIDDEN_STRINGS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_transition",
    "auto_fade",
    "auto_j_cut",
    "auto_l_cut",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
    "apply_cut",
    "render_now",
    "execute_cut",
    "final_cut",
    "apply_transition",
]

ALLOWED_REVIEW_STRINGS = [
    "hard_cut_review",
    "j_cut_review",
    "l_cut_review",
    "quick_fade_review",
    "no_cut_protect",
    "censor_safe_keep",
    "technical_transition_review",
    "transition_unknown_review",
    "review_hard_cut_transition",
    "review_j_cut_transition",
    "review_l_cut_transition",
    "review_quick_fade_transition",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _transition_decision_pipeline_block() -> str:
    text = _read(PIPELINE_FILE)
    start_marker = "# -- Transition Decision Engine (2B-29-C)"
    end_marker = "# -- End Transition Decision Engine"

    assert start_marker in text
    assert end_marker in text

    start = text.index(start_marker)
    end = text.index(end_marker, start)

    return text[start:end]


def _safe_forbidden_scan_text(text: str) -> str:
    return text.replace(
        "apply_transition_decision_run_report_to_job",
        "write_transition_decision_run_report_to_job",
    )


def test_all_2b29_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), path


def test_all_2b29_tests_exist():
    for path in TEST_FILES:
        assert path.exists(), path


def test_job_transition_decision_fields_exist_and_old_jobs_load():
    data = {
        "job_id": "job_transition_decision_final_audit",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }

    job = Job.from_dict(data)
    job_dict = job.to_dict()

    expected_fields = [
        "transition_decision_report",
        "transition_decision_status",
        "transition_decision_decisions",
        "transition_decision_count",
        "transition_decision_hard_cut_review_count",
        "transition_decision_j_cut_review_count",
        "transition_decision_l_cut_review_count",
        "transition_decision_quick_fade_review_count",
        "transition_decision_no_cut_protect_count",
        "transition_decision_censor_safe_keep_count",
        "transition_decision_technical_review_count",
        "transition_decision_unknown_review_count",
        "transition_decision_recommendation",
    ]

    for field in expected_fields:
        assert field in job_dict

    assert job.transition_decision_report == {}
    assert job.transition_decision_decisions == []
    assert job.transition_decision_count == 0
    assert job.transition_decision_recommendation is None


def test_pipeline_contains_transition_decision_block():
    text = _read(PIPELINE_FILE)
    block = _transition_decision_pipeline_block()

    assert "from core.transition_decision_runner import (" in text
    assert "run_transition_decision_for_job" in text
    assert "apply_transition_decision_run_report_to_job" in text

    assert "TRANSITION_DECISION_STARTED" in block
    assert "TRANSITION_DECISION_DONE" in block
    assert "TRANSITION_DECISION_SKIPPED" in block
    assert "TRANSITION_DECISION_FAILED" in block
    assert 'step_name="transition_decision_done"' in block


def test_pipeline_position_is_after_clip_duration_optimization():
    text = _read(PIPELINE_FILE)

    clip_duration_done_index = text.index('step_name="clip_duration_optimization_done"')
    transition_decision_index = text.index("# -- Transition Decision Engine (2B-29-C)")

    assert transition_decision_index > clip_duration_done_index


def test_pipeline_block_uses_runner_apply_and_safe_exception_handling():
    block = _transition_decision_pipeline_block()

    assert "transition_decision_report = run_transition_decision_for_job" in block
    assert "apply_transition_decision_run_report_to_job(" in block
    assert "try:" in block
    assert "except Exception as transition_decision_exc:" in block
    assert 'job.transition_decision_status = "failed"' in block
    assert 'job.transition_decision_recommendation = "transition_decision_failed"' in block


def test_registry_contains_transition_decision_source_and_adapter():
    text = _read(REGISTRY_FILE)

    assert "adapt_transition_decision_report_to_signals" in text
    assert 'SOURCE_TRANSITION_DECISION = "transition_decision"' in text
    assert "transition_decision_report" in text
    assert "transition_decision_decisions" in text
    assert "source_counts[SOURCE_TRANSITION_DECISION]" in text


def test_registry_keeps_existing_sources():
    text = _read(REGISTRY_FILE)

    existing_sources = [
        "clip_duration_optimizer",
        "cut_list_generator",
        "murch_scoring",
        "segment_classifier",
        "content_value",
        "profanity_censor",
        "dead_content",
        "sentence_boundary",
        "keyword_emotion",
        "interaction_classification",
        "scene_change",
        "motion_analysis",
        "face_reaction",
        "stutter_detection",
        "screen_content",
        "visual_energy",
    ]

    for source in existing_sources:
        assert source in text


def test_product_files_do_not_contain_forbidden_execution_strings():
    for path in PRODUCT_FILES:
        text = _safe_forbidden_scan_text(_read(path).lower())
        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_allowed_review_suggestion_strings_exist():
    combined = "\n".join(_read(path) for path in PRODUCT_FILES)

    for allowed in ALLOWED_REVIEW_STRINGS:
        assert allowed in combined


def test_product_files_do_not_import_timeline_or_highlight_selector():
    forbidden = [
        "TimelineBuilder",
        "LongformTimelineBuilder",
        "HighlightSelector",
        "highlight_selector",
    ]

    for path in PRODUCT_FILES:
        text = _read(path)
        for word in forbidden:
            assert word not in text, f"{word} found in {path}"


def test_transition_decision_pipeline_block_does_not_execute_cut_render_or_timeline_apply():
    block = _safe_forbidden_scan_text(_transition_decision_pipeline_block().lower())

    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
        "auto_transition",
        "auto_fade",
        "auto_j_cut",
        "auto_l_cut",
        "auto_highlight",
        "highlight_now",
        "auto_hook",
        "auto_mute",
        "censor_now",
        "delete_segment",
        "drop_segment",
        "timeline_apply_now",
        "apply_cut",
        "render_now",
        "execute_cut",
        "final_cut",
        "apply_transition",
        "ffmpeg",
        "render_processor",
        "finalrenderdriver",
        "longformtimelinebuilder",
        "highlightselector",
    ]

    for word in forbidden:
        assert word not in block


def test_transition_decision_signal_types_are_supported():
    text = _read(ROOT / "core" / "transition_decision_signal_adapter.py")

    expected_signal_types = [
        "transition_hard_cut_review",
        "transition_j_cut_review",
        "transition_l_cut_review",
        "transition_quick_fade_review",
        "transition_no_cut_protect",
        "transition_censor_safe_keep",
        "transition_technical_review",
        "transition_unknown_review",
    ]

    for signal_type in expected_signal_types:
        assert signal_type in text


def test_no_bom_and_newline_for_all_2b29_files():
    all_files = PRODUCT_FILES + TEST_FILES + [
        PIPELINE_FILE,
        REGISTRY_FILE,
        JOB_FILE,
    ]

    for path in all_files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
