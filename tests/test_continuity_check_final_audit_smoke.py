from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "continuity_check.py",
    ROOT / "core" / "continuity_checker.py",
    ROOT / "models" / "continuity_check_run.py",
    ROOT / "core" / "continuity_check_runner.py",
    ROOT / "core" / "continuity_check_signal_adapter.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_continuity_check_foundation_smoke.py",
    ROOT / "tests" / "test_continuity_check_runner_smoke.py",
    ROOT / "tests" / "test_continuity_check_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_continuity_check_signal_adapter_smoke.py",
    ROOT / "tests" / "test_continuity_check_registry_integration_smoke.py",
    ROOT / "tests" / "test_continuity_check_final_audit_smoke.py",
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
    "review_sentence_boundary_continuity",
    "review_context_jump_continuity",
    "protect_censor_context_continuity",
    "review_timing_continuity",
    "review_transition_conflict",
    "review_technical_continuity",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _continuity_check_pipeline_block() -> str:
    text = _read(PIPELINE_FILE)
    start_marker = "# -- Continuity Check (2B-30-C)"
    end_marker = "# -- End Continuity Check"

    assert start_marker in text
    assert end_marker in text

    start = text.index(start_marker)
    end = text.index(end_marker, start)

    return text[start:end]


def test_all_2b30_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), path


def test_all_2b30_tests_exist():
    for path in TEST_FILES:
        assert path.exists(), path


def test_job_continuity_check_fields_exist_and_old_jobs_load():
    data = {
        "job_id": "job_continuity_check_final_audit",
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
        "continuity_check_report",
        "continuity_check_status",
        "continuity_check_issues",
        "continuity_check_issue_count",
        "continuity_check_blocking_issue_count",
        "continuity_check_sentence_break_risk_count",
        "continuity_check_context_jump_risk_count",
        "continuity_check_censor_context_risk_count",
        "continuity_check_timing_issue_count",
        "continuity_check_transition_conflict_count",
        "continuity_check_technical_issue_count",
        "continuity_check_protected_context_count",
        "continuity_check_recommendation",
    ]

    for field in expected_fields:
        assert field in job_dict

    assert job.continuity_check_report == {}
    assert job.continuity_check_issues == []
    assert job.continuity_check_issue_count == 0
    assert job.continuity_check_recommendation is None


def test_pipeline_contains_continuity_check_block():
    text = _read(PIPELINE_FILE)
    block = _continuity_check_pipeline_block()

    assert "from core.continuity_check_runner import (" in text
    assert "run_continuity_check_for_job" in text
    assert "apply_continuity_check_run_report_to_job" in text
    assert "CONTINUITY_CHECK_STARTED" in block
    assert "CONTINUITY_CHECK_DONE" in block
    assert "CONTINUITY_CHECK_SKIPPED" in block
    assert "CONTINUITY_CHECK_FAILED" in block
    assert 'step_name="continuity_check_done"' in block


def test_pipeline_position_is_after_transition_decision():
    text = _read(PIPELINE_FILE)

    transition_decision_done_index = text.index('step_name="transition_decision_done"')
    continuity_check_index = text.index("# -- Continuity Check (2B-30-C)")

    assert continuity_check_index > transition_decision_done_index


def test_pipeline_block_uses_runner_apply_and_safe_exception_handling():
    block = _continuity_check_pipeline_block()

    assert "continuity_check_report = run_continuity_check_for_job" in block
    assert "apply_continuity_check_run_report_to_job(" in block
    assert "try:" in block
    assert "except Exception as continuity_check_exc:" in block
    assert 'job.continuity_check_status = "failed"' in block
    assert 'job.continuity_check_recommendation = "continuity_check_failed"' in block


def test_registry_contains_continuity_check_source_and_adapter():
    text = _read(REGISTRY_FILE)

    assert "adapt_continuity_check_report_to_signals" in text
    assert 'SOURCE_CONTINUITY_CHECK = "continuity_check"' in text
    assert "continuity_check_report" in text
    assert "continuity_check_issues" in text
    assert "source_counts[SOURCE_CONTINUITY_CHECK]" in text


def test_registry_keeps_existing_sources():
    text = _read(REGISTRY_FILE)

    existing_sources = [
        "transition_decision",
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
        text = _read(path).lower()
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


def test_continuity_check_pipeline_block_does_not_execute_cut_render_or_timeline_apply():
    block = _continuity_check_pipeline_block().lower()

    forbidden = FORBIDDEN_STRINGS + [
        "ffmpeg",
        "render_processor",
        "finalrenderdriver",
        "longformtimelinebuilder",
        "highlightselector",
    ]

    for word in forbidden:
        assert word not in block


def test_continuity_check_signal_types_are_supported():
    text = _read(ROOT / "core" / "continuity_check_signal_adapter.py")

    expected_signal_types = [
        "continuity_sentence_break_risk",
        "continuity_context_jump_risk",
        "continuity_censor_context_risk",
        "continuity_timing_issue",
        "continuity_transition_conflict",
        "continuity_protected_context_violation",
        "continuity_technical_risk",
        "continuity_unknown_review",
    ]

    for signal_type in expected_signal_types:
        assert signal_type in text


def test_no_bom_and_newline_for_all_2b30_files():
    all_files = PRODUCT_FILES + TEST_FILES + [
        PIPELINE_FILE,
        REGISTRY_FILE,
        JOB_FILE,
    ]

    for path in all_files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
