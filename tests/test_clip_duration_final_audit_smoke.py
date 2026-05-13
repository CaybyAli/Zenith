from pathlib import Path

from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "clip_duration.py",
    ROOT / "core" / "clip_duration_optimizer.py",
    ROOT / "models" / "clip_duration_run.py",
    ROOT / "core" / "clip_duration_runner.py",
    ROOT / "core" / "clip_duration_signal_adapter.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_clip_duration_optimizer_foundation_smoke.py",
    ROOT / "tests" / "test_clip_duration_runner_smoke.py",
    ROOT / "tests" / "test_clip_duration_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_clip_duration_signal_adapter_smoke.py",
    ROOT / "tests" / "test_clip_duration_registry_integration_smoke.py",
    ROOT / "tests" / "test_clip_duration_final_audit_smoke.py",
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
    "auto_extend",
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
]

ALLOWED_STRINGS = [
    "REVIEW_TRIM",
    "review_trim_duration_candidate",
    "review_extend_duration_candidate",
    "suggested_start_seconds",
    "suggested_end_seconds",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _clip_duration_pipeline_block() -> str:
    text = _read(PIPELINE_FILE)
    start_marker = "# -- Clip Duration Optimization (2B-28-C)"
    end_marker = "# -- End Clip Duration Optimization"

    assert start_marker in text
    assert end_marker in text

    start = text.index(start_marker)
    end = text.index(end_marker, start)

    return text[start:end]


def test_all_2b28_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), path


def test_all_2b28_tests_exist():
    for path in TEST_FILES:
        assert path.exists(), path


def test_job_clip_duration_fields_exist_and_old_jobs_load():
    data = {
        "job_id": "job_clip_duration_final_audit",
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
        "clip_duration_report",
        "clip_duration_status",
        "clip_duration_recommendations",
        "clip_duration_recommendation_count",
        "clip_duration_ok_count",
        "clip_duration_too_short_count",
        "clip_duration_too_long_count",
        "clip_duration_trim_review_count",
        "clip_duration_extend_review_count",
        "clip_duration_protect_duration_count",
        "clip_duration_censor_keep_count",
        "clip_duration_technical_review_count",
        "clip_duration_invalid_timing_count",
        "clip_duration_recommendation",
    ]

    for field in expected_fields:
        assert field in job_dict

    assert job.clip_duration_report == {}
    assert job.clip_duration_recommendations == []
    assert job.clip_duration_recommendation_count == 0
    assert job.clip_duration_recommendation is None


def test_pipeline_contains_clip_duration_optimization_block():
    text = _read(PIPELINE_FILE)
    block = _clip_duration_pipeline_block()

    assert "from core.clip_duration_runner import (" in text
    assert "run_clip_duration_optimization_for_job" in text
    assert "apply_clip_duration_run_report_to_job" in text

    assert "CLIP_DURATION_OPTIMIZATION_STARTED" in block
    assert "CLIP_DURATION_OPTIMIZATION_DONE" in block
    assert "CLIP_DURATION_OPTIMIZATION_SKIPPED" in block
    assert "CLIP_DURATION_OPTIMIZATION_FAILED" in block
    assert 'step_name="clip_duration_optimization_done"' in block


def test_pipeline_position_is_after_cut_list_generation():
    text = _read(PIPELINE_FILE)

    cut_list_done_index = text.index('step_name="cut_list_generation_done"')
    clip_duration_index = text.index("# -- Clip Duration Optimization (2B-28-C)")

    assert clip_duration_index > cut_list_done_index


def test_registry_contains_clip_duration_source_and_adapter():
    text = _read(REGISTRY_FILE)

    assert "adapt_clip_duration_report_to_signals" in text
    assert 'SOURCE_CLIP_DURATION_OPTIMIZER = "clip_duration_optimizer"' in text
    assert "clip_duration_report" in text
    assert "clip_duration_recommendations" in text
    assert "source_counts[SOURCE_CLIP_DURATION_OPTIMIZER]" in text


def test_registry_keeps_existing_sources():
    text = _read(REGISTRY_FILE)

    existing_sources = [
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

    for allowed in ALLOWED_STRINGS:
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


def test_clip_duration_pipeline_block_does_not_execute_cut_render_or_timeline_apply():
    block = _clip_duration_pipeline_block().lower()

    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
        "auto_extend",
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
        "ffmpeg",
        "render_processor",
        "finalrenderdriver",
        "longformtimelinebuilder",
        "highlightselector",
    ]

    for word in forbidden:
        assert word not in block


def test_duration_statuses_are_supported_in_foundation():
    text = _read(ROOT / "core" / "clip_duration_optimizer.py")

    expected_statuses = [
        "duration_ok",
        "too_short_review",
        "too_long_review",
        "trim_review",
        "extend_review",
        "protect_duration",
        "censor_keep_duration",
        "technical_review",
        "invalid_timing_review",
        "unknown_review",
    ]

    for status in expected_statuses:
        assert status in text


def test_signal_adapter_supports_required_signal_types():
    text = _read(ROOT / "core" / "clip_duration_signal_adapter.py")

    expected_signal_types = [
        "clip_duration_ok",
        "clip_duration_too_short_review",
        "clip_duration_too_long_review",
        "clip_duration_protected",
        "clip_duration_censor_keep",
        "clip_duration_technical_review",
        "clip_duration_invalid_timing",
        "clip_duration_unknown_review",
    ]

    for signal_type in expected_signal_types:
        assert signal_type in text


def test_no_bom_and_newline_for_all_2b28_files():
    all_files = PRODUCT_FILES + TEST_FILES + [
        PIPELINE_FILE,
        REGISTRY_FILE,
        JOB_FILE,
    ]

    for path in all_files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
