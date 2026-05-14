from pathlib import Path

PRODUCT_FILES = [
    Path("models/render_dashboard_delivery_package.py"),
    Path("core/render_dashboard_delivery_package_builder.py"),
    Path("core/render_dashboard_delivery_package_runner.py"),
    Path("core/render_dashboard_delivery_package_signal_adapter.py"),
]

INTEGRATION_FILES = [
    Path("core/gaming_pipeline.py"),
    Path("core/unified_edit_signal_registry.py"),
    Path("models/job.py"),
]

FORBIDDEN_IN_NEW_FILES = [
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
    "full_render",
    "render_timeline",
    "project_output",
    "user_media_input",
    "start_render",
    "export_video",
    "mkdir",
    "makedirs",
    "write_text",
    "write_bytes",
    "shutil",
    "copyfile",
    "move",
    "rename",
    "thumbnail",
    "extract_frame",
    "dashboard_file",
]

FORBIDDEN_2B57_INTEGRATION_TOKENS = [
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "shell=True",
    "RenderProcessor",
    "TimelineBuilder",
    "moviepy",
    "cv2.VideoWriter",
    "write_videofile",
    "apply_timeline",
    "execute_timeline",
    "start_render",
    "export_video",
    "write_text",
    "write_bytes",
    "shutil",
    "copyfile",
    "rename",
]


def test_render_dashboard_delivery_product_files_have_no_forbidden_operations() -> None:
    for path in PRODUCT_FILES:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_IN_NEW_FILES:
            assert token not in text, f"{token} found in {path}"


def test_render_dashboard_delivery_integration_files_have_safe_2b57_blocks() -> None:
    for path in INTEGRATION_FILES:
        text = path.read_text(encoding="utf-8")
        if "2B-57" not in text and "render_dashboard_delivery" not in text:
            continue

        relevant_lines = [
            line
            for line in text.splitlines()
            if "2B-57" in line or "render_dashboard_delivery" in line
        ]
        relevant_text = "\n".join(relevant_lines)

        for token in FORBIDDEN_2B57_INTEGRATION_TOKENS:
            assert token not in relevant_text, f"{token} found in 2B-57 block of {path}"


def test_render_dashboard_delivery_files_have_no_bom_and_end_with_newline() -> None:
    for path in [*PRODUCT_FILES, *INTEGRATION_FILES]:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
