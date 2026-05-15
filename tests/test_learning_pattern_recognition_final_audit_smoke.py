from pathlib import Path


PRODUCT_FILES = [
    Path("models/learning_pattern_recognition.py"),
    Path("core/learning_pattern_recognition.py"),
    Path("core/learning_pattern_recognition_runner.py"),
    Path("core/learning_pattern_recognition_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

STRICT_PRODUCT_FILES = [
    Path("models/learning_pattern_recognition.py"),
    Path("core/learning_pattern_recognition.py"),
    Path("core/learning_pattern_recognition_runner.py"),
    Path("core/learning_pattern_recognition_signal_adapter.py"),
]

FORBIDDEN_STRICT_TOKENS = [
    "subprocess",
    "os.system",
    "shell=True",
    "subprocess.run",
    "subprocess.Popen",
    "ffmpeg",
    "ffprobe",
    "execute_final_cutlist",
    "apply_final_cutlist",
    "TimelineBuilder",
    "HighlightSelector",
    "RenderProcessor",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "apply_timeline",
    "execute_timeline",
    "reorder_timeline",
    "move_clip",
    "split_clip",
    "merge_clip",
    "style_dna.write",
    "write_style_dna",
    "save_style_dna",
    "update_style_dna_file",
    "profile.write",
    "update_profile",
    "change_profile",
    "publish_video",
    "upload_video",
    "autopublish",
    "start_render",
    "trigger_render",
    "write_text",
    "write_bytes",
    "mkdir",
    "makedirs",
]


def test_learning_pattern_product_files_have_no_bom_and_end_with_newline():
    for path in PRODUCT_FILES:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path


def test_learning_pattern_new_product_files_do_not_contain_forbidden_actions():
    allowed_data_field_fragments = [
        "can_update_style_dna",
        "can_write_style_dna",
        "can_change_profile",
        "can_change_cutting_rules",
        "can_modify_timeline",
        "can_trigger_render",
        "can_publish",
        "no_style_dna_file_write_in_2b_64",
        "no_profile_change_in_2b_64",
        "no_cutting_rule_activation_in_2b_64",
        "no_timeline_modify_in_2b_64",
        "no_render_trigger_in_2b_64",
        "no_publish_in_2b_64",
    ]

    for path in STRICT_PRODUCT_FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if any(fragment in line for fragment in allowed_data_field_fragments):
                continue
            for token in FORBIDDEN_STRICT_TOKENS:
                assert token not in line, f"{token} found in {path}:{line_number}"


def test_learning_pattern_pipeline_and_registry_only_contain_data_only_markers():
    pipeline = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    registry = Path("core/unified_edit_signal_registry.py").read_text(encoding="utf-8")

    assert "run_learning_pattern_recognition_for_job(job)" in pipeline
    assert "learning_pattern_recognition_done" in pipeline
    assert "build_learning_pattern_recognition_signals" in registry
    assert "SOURCE_LEARNING_PATTERN_RECOGNITION" in registry

    assert "learning_pattern_recognition_only" in pipeline
    assert "feedback_trend_analysis_only" in pipeline
    assert "learning_pattern_recognition" in registry


def test_learning_pattern_safety_flags_are_hard_false_in_runner_and_job():
    runner = Path("core/learning_pattern_recognition_runner.py").read_text(
        encoding="utf-8"
    )
    job_model = Path("models/job.py").read_text(encoding="utf-8")

    for field in [
        "learning_pattern_can_update_style_dna",
        "learning_pattern_can_write_style_dna",
        "learning_pattern_can_change_profile",
        "learning_pattern_can_change_cutting_rules",
        "learning_pattern_can_modify_timeline",
        "learning_pattern_can_trigger_render",
        "learning_pattern_can_publish",
    ]:
        assert f'_assign(job, "{field}", False)' in runner
        assert f"{field}=False" in job_model
