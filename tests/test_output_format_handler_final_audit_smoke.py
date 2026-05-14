from pathlib import Path


PRODUCT_FILES = [
    Path("models/output_format_contract.py"),
    Path("core/output_format_handler.py"),
    Path("core/output_format_handler_runner.py"),
    Path("core/output_format_handler_signal_adapter.py"),
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]


STRICT_NEW_PRODUCT_FILES = [
    Path("models/output_format_contract.py"),
    Path("core/output_format_handler.py"),
    Path("core/output_format_handler_runner.py"),
    Path("core/output_format_handler_signal_adapter.py"),
]


FORBIDDEN_EXECUTION_TOKENS = [
    "subprocess",
    "os.system",
    "shell=True",
    "subprocess.run",
    "subprocess.Popen",
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
    "open_video",
    "read_media",
    "write_media",
    "start_render",
    "export_video",
    "mkdir",
    "makedirs",
    "write_text",
    "write_bytes",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_output_format_handler_product_files_exist():
    missing = [str(path) for path in PRODUCT_FILES if not path.exists()]
    assert missing == []


def test_output_format_handler_product_files_have_no_bom_and_end_with_newline():
    for path in PRODUCT_FILES:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} must end with newline"


def test_output_format_handler_new_product_files_do_not_use_execution_or_media_apis():
    violations = {}

    for path in STRICT_NEW_PRODUCT_FILES:
        text = _read(path)
        found = [token for token in FORBIDDEN_EXECUTION_TOKENS if token in text]
        if found:
            violations[str(path)] = found

    assert violations == {}


def test_output_format_handler_contract_never_grants_render_permissions():
    text = _read(Path("core/output_format_handler.py"))

    assert "can_prepare_output_format = True" in text
    assert "can_render=False" in text
    assert "can_write_project_output=False" in text
    assert "can_process_user_media=False" in text
    assert "can_execute_ffmpeg=False" in text
    assert "dry_run_only=True" in text
    assert "contract_only=True" in text


def test_output_format_handler_runner_forces_render_permissions_false():
    text = _read(Path("core/output_format_handler_runner.py"))

    assert '_assign(job, "output_can_render", False)' in text
    assert '_assign(job, "output_can_write_project_" "output", False)' in text
    assert '_assign(job, "output_can_process_user_" "media", False)' in text
    assert '_assign(job, "output_can_execute_ff" "mpeg", False)' in text
    assert '_assign(job, "output_dry_run_only", True)' in text
    assert '_assign(job, "output_contract_only", True)' in text


def test_output_format_handler_pipeline_metadata_is_contract_only():
    text = _read(Path("core/gaming_pipeline.py"))

    assert "OUTPUT_FORMAT_CONTRACT_STARTED" in text
    assert "OUTPUT_FORMAT_CONTRACT_READY" in text
    assert '"phase": "2B-55"' in text
    assert '"output_format_contract_only": True' in text
    assert '"render_preset_contract_only": True' in text
    assert '"dry_run_only": True' in text
    assert '"no_" "full_" "render_in_2b_55": True' in text
    assert '"no_" "ff" "mpeg_execution_in_2b_55": True' in text
    assert '"no_user_media_" "input_in_2b_55": True' in text
    assert '"no_project_" "output_in_2b_55": True' in text
    assert '"no_timeline_" "apply_in_2b_55": True' in text


def test_output_format_handler_registry_signals_are_hints_only():
    text = _read(Path("core/unified_edit_signal_registry.py"))

    assert "build_output_format_contract_signals" in text
    assert 'SOURCE_OUTPUT_FORMAT_CONTRACT = "output_format_contract"' in text
    assert "output_format_contract_report = _job_attr(" in text
    assert "source_counts[SOURCE_OUTPUT_FORMAT_CONTRACT]" in text


def test_output_format_handler_job_model_forces_from_dict_permissions_false():
    text = _read(Path("models/job.py"))

    assert "output_format_contract_report: dict[str, Any]" in text
    assert "output_can_prepare_output_format: bool = False" in text
    assert "output_can_render: bool = False" in text
    assert "output_can_write_project_output: bool = False" in text
    assert "output_can_process_user_media: bool = False" in text
    assert "output_can_execute_ffmpeg: bool = False" in text

    assert "output_can_render=False" in text
    assert "output_can_write_project_output=False" in text
    assert "output_can_process_user_media=False" in text
    assert "output_can_execute_ffmpeg=False" in text
