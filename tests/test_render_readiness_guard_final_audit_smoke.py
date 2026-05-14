from pathlib import Path


PRODUCT_FILES = [
    "models/render_readiness_guard.py",
    "core/render_readiness_guard.py",
    "core/render_readiness_guard_runner.py",
    "core/render_readiness_guard_signal_adapter.py",
]

INTEGRATION_FILES = [
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]

ALL_AUDIT_FILES = PRODUCT_FILES + INTEGRATION_FILES

FORBIDDEN_IMPORT_OR_CALL_TOKENS = [
    "subprocess",
    "os.system",
    "ffprobe",
    "render_video",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "delete_media",
    "remove_file",
    "trim_now",
    "censor_now",
    "mute_track",
    "apply_timeline(",
    "execute_timeline(",
    "reorder_timeline(",
    "move_clip(",
    "split_clip(",
    "merge_clip(",
    "open_video",
    "read_media",
    "write_media",
    "export_video",
    "start_render(",
]

ALLOWED_RENDER_READINESS_MARKERS = [
    "render_readiness_guard_only",
    "media_unchanged",
    "no_execution_in_2b_45",
    "no_render_in_2b_45",
    "no_ffmpeg_in_2b_45",
    "no_media_write_in_2b_45",
    "no_timeline_apply_in_2b_45",
    "ready_for_next_render_stage",
    "can_start_render_pipeline",
    "can_render",
    "can_run_ffmpeg",
    "can_execute_media_operations",
    "can_apply_timeline",
    "can_modify_media",
]


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_render_readiness_audit_files_exist():
    missing = [path for path in ALL_AUDIT_FILES if not Path(path).is_file()]

    assert missing == []


def test_render_readiness_audit_files_have_no_bom_and_end_with_newline():
    bad_bom = []
    bad_newline = []

    for path in ALL_AUDIT_FILES:
        raw = Path(path).read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            bad_bom.append(path)
        if raw and not raw.endswith(b"\n"):
            bad_newline.append(path)

    assert bad_bom == []
    assert bad_newline == []


def test_render_readiness_product_files_do_not_use_media_or_execution_operations():
    violations = {}

    for path in PRODUCT_FILES:
        text = _read(path)
        found = [
            token
            for token in FORBIDDEN_IMPORT_OR_CALL_TOKENS
            if token in text
        ]
        if found:
            violations[path] = found

    assert violations == {}


def test_render_readiness_product_files_keep_all_media_execution_flags_false():
    combined_text = "\n".join(_read(path) for path in PRODUCT_FILES)

    assert "can_render=False" in combined_text or '"can_render"] = False' in combined_text or '"can_render": False' in combined_text
    assert "can_run_ffmpeg=False" in combined_text or '"can_run_ffmpeg"] = False' in combined_text or '"can_run_ffmpeg": False' in combined_text
    assert "can_execute_media_operations=False" in combined_text or '"can_execute_media_operations"] = False' in combined_text or '"can_execute_media_operations": False' in combined_text
    assert "can_apply_timeline=False" in combined_text or '"can_apply_timeline"] = False' in combined_text or '"can_apply_timeline": False' in combined_text
    assert "can_modify_media=False" in combined_text or '"can_modify_media"] = False' in combined_text or '"can_modify_media": False' in combined_text


def test_render_readiness_product_files_include_required_safety_metadata():
    combined_text = "\n".join(_read(path) for path in PRODUCT_FILES)
    missing = [
        marker
        for marker in ALLOWED_RENDER_READINESS_MARKERS
        if marker not in combined_text
    ]

    assert missing == []


def test_pipeline_contains_render_readiness_guard_after_final_quality():
    text = _read("core/gaming_pipeline.py")

    assert "from core.render_readiness_guard_runner import run_render_readiness_guard" in text
    assert "run_final_quality_validator(job)" in text
    assert "run_render_readiness_guard(job)" in text
    assert text.index("run_final_quality_validator(job)") < text.index("run_render_readiness_guard(job)")
    assert 'step_name="final_quality_validator_done"' in text
    assert 'step_name="render_readiness_guard_done"' in text

    required_tokens = [
        '"phase": "2B-45"',
        '"block": "block8_render_export"',
        '"render_readiness_guard_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_45": True',
        '"no_render_in_2b_45": True',
        '"no_ff" "mpeg_in_2b_45": True',
        '"no_media_write_in_2b_45": True',
        '"no_timeline_" "apply_" "in_2b_45": True',
        '"can_render": False',
        '"can_run_" "ff" "mpeg": False',
        '"can_execute_media_operations": False',
        '"can_" "apply_" "timeline": False',
        '"can_modify_media": False',
    ]

    missing = [token for token in required_tokens if token not in text]

    assert missing == []


def test_registry_contains_render_readiness_source_and_adapter():
    text = _read("core/unified_edit_signal_registry.py")

    required_tokens = [
        "build_render_readiness_guard_signals",
        'SOURCE_RENDER_READINESS_GUARD = "render_readiness_guard"',
        "render_readiness_guard_signals = _safe_collect",
        "SOURCE_RENDER_READINESS_GUARD",
    ]

    missing = [token for token in required_tokens if token not in text]

    assert missing == []


def test_job_model_contains_render_readiness_fields_and_safe_from_dict_defaults():
    text = _read("models/job.py")

    required_fields = [
        "render_readiness_guard_report",
        "render_readiness_guard",
        "render_readiness_status",
        "render_readiness_checks",
        "render_readiness_total_checks",
        "render_readiness_passed_count",
        "render_readiness_warning_count",
        "render_readiness_blocking_count",
        "render_readiness_review_required",
        "render_readiness_ready_for_next_render_stage",
        "render_readiness_can_start_render_pipeline",
        "render_readiness_can_render",
        "render_readiness_can_run_ffmpeg",
        "render_readiness_can_execute_media_operations",
        "render_readiness_can_apply_timeline",
        "render_readiness_can_modify_media",
        "render_readiness_blocking_reasons",
        "render_readiness_warnings",
        "render_readiness_recommendation",
    ]

    missing = [field for field in required_fields if field not in text]

    assert missing == []

    assert "render_readiness_can_render=False" in text
    assert "render_readiness_can_run_ffmpeg=False" in text
    assert "render_readiness_can_execute_media_operations=False" in text
    assert "render_readiness_can_apply_timeline=False" in text
    assert "render_readiness_can_modify_media=False" in text
