from pathlib import Path


PRODUCT_FILES = [
    Path("models/final_quality_validator.py"),
    Path("core/final_quality_validator.py"),
    Path("core/final_quality_validator_runner.py"),
    Path("core/final_quality_validator_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

STRICT_FINAL_QUALITY_FILES = [
    Path("models/final_quality_validator.py"),
    Path("core/final_quality_validator.py"),
    Path("core/final_quality_validator_runner.py"),
    Path("core/final_quality_validator_signal_adapter.py"),
]

FORBIDDEN_TOKENS = [
    "subprocess",
    "os.system",
    "ffmpeg",
    "render_video",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "delete_media",
    "remove_file",
    "trim_now",
    "censor_now",
    "mute_track",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "apply_quality_fix",
    "execute_quality_fix",
    "auto_fix",
    "auto_correct",
    "auto_remove",
    "auto_trim",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _strip_allowed_safety_field_names(text: str) -> str:
    allowed_tokens = [
        "can_apply_fixes",
        "can_render",
        "can_execute_timeline",
        "can_reorder_timeline",
        "can_trim",
        "can_extend",
        "can_insert_effects",
        "final_quality_can_apply_fixes",
        "final_quality_can_render",
        "final_quality_can_execute_timeline",
        "final_quality_can_reorder_timeline",
        "final_quality_can_trim",
        "final_quality_can_extend",
        "final_quality_can_insert_effects",
        "no_execution_in_2b_43",
        "no_render_in_2b_43",
        "no_timeline_reorder_in_2b_43",
        "no_quality_fix_apply_in_2b_43",
    ]
    cleaned = text
    for token in allowed_tokens:
        cleaned = cleaned.replace(token, "")
    return cleaned


def test_final_quality_product_files_exist():
    for path in PRODUCT_FILES:
        assert path.exists(), f"missing product file: {path}"


def test_final_quality_product_files_have_no_bom_and_end_with_newline():
    for path in PRODUCT_FILES:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert data.endswith(b"\n"), f"missing trailing newline in {path}"


def test_strict_final_quality_files_do_not_use_forbidden_media_operations():
    for path in STRICT_FINAL_QUALITY_FILES:
        text = _strip_allowed_safety_field_names(_read(path))
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"forbidden token {token!r} found in {path}"


def test_gaming_pipeline_final_quality_block_is_review_only_and_safe():
    text = _read(Path("core/gaming_pipeline.py"))

    start = text.index('phase="2B-43"')
    end = text.index("except Exception as pattern_interrupt_exc", start)
    block = text[start:end]
    unsafe_block = _strip_allowed_safety_field_names(block)

    required = [
        "run_final_quality_validator(job)",
        'step_name="final_quality_validator_done"',
        '"review_only": True',
        '"final_quality_validator_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_43": True',
        '"no_render_in_2b_43": True',
        '"no_timeline_reorder_in_2b_43": True',
        '"no_quality_fix_apply_in_2b_43": True',
        '"can_apply_fixes": False',
        '"can_render": False',
        '"can_execute_timeline": False',
        '"can_reorder_timeline": False',
        '"can_trim": False',
        '"can_extend": False',
        '"can_insert_effects": False',
    ]

    for token in required:
        assert token in block

    forbidden_in_block = [
        "render_video",
        "execute_final_cutlist",
        "apply_final_cutlist",
        "TimelineBuilder",
        "HighlightSelector",
        "moviepy",
        "cv2.VideoWriter",
        "write_videofile",
        "delete_media",
        "remove_file",
        "trim_now",
        "censor_now",
        "mute_track",
        "apply_timeline",
        "execute_timeline",
        "reorder_timeline",
        "move_clip",
        "split_clip",
        "merge_clip",
        "apply_quality_fix",
        "execute_quality_fix",
        "auto_fix",
        "auto_correct",
        "auto_remove",
        "auto_trim",
    ]

    for token in forbidden_in_block:
        assert token not in unsafe_block, f"forbidden token {token!r} found in 2B-43 pipeline block"


def test_job_final_quality_fields_are_locked_to_safe_defaults():
    text = _read(Path("models/job.py"))

    required = [
        "final_quality_validation_report: dict[str, Any] = field(default_factory=dict)",
        "final_quality_checks: list[dict[str, Any]] = field(default_factory=list)",
        "final_quality_suggestions: list[dict[str, Any]] = field(default_factory=list)",
        "final_quality_can_apply_fixes: bool = False",
        "final_quality_can_render: bool = False",
        "final_quality_can_execute_timeline: bool = False",
        "final_quality_can_reorder_timeline: bool = False",
        "final_quality_can_trim: bool = False",
        "final_quality_can_extend: bool = False",
        "final_quality_can_insert_effects: bool = False",
        "final_quality_can_apply_fixes=False",
        "final_quality_can_render=False",
        "final_quality_can_execute_timeline=False",
        "final_quality_can_reorder_timeline=False",
        "final_quality_can_trim=False",
        "final_quality_can_extend=False",
        "final_quality_can_insert_effects=False",
    ]

    for token in required:
        assert token in text


def test_registry_final_quality_signals_are_review_only():
    text = _read(Path("core/unified_edit_signal_registry.py"))

    assert 'SOURCE_FINAL_QUALITY_VALIDATOR = "final_quality_validator"' in text
    assert "build_final_quality_validator_signals" in text
    assert "SOURCE_FINAL_QUALITY_VALIDATOR" in text
    assert 'lambda: {"signals": build_final_quality_validator_signals(job)}' in text
