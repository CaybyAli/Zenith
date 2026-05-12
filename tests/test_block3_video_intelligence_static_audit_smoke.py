from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


BLOCK3_IMPLEMENTATION_FILES = {
    "2B-13 Scene Change Detection": [
        "models/scene_change.py",
        "core/scene_change_detector.py",
        "models/scene_change_source.py",
        "models/scene_change_run.py",
        "core/scene_change_source_selector.py",
        "core/scene_change_runner.py",
        "core/scene_change_signal_adapter.py",
    ],
    "2B-14 Motion Analysis": [
        "models/motion_analysis.py",
        "core/motion_analyzer.py",
        "models/motion_analysis_source.py",
        "models/motion_analysis_run.py",
        "core/motion_analysis_source_selector.py",
        "core/motion_analysis_runner.py",
        "core/motion_analysis_signal_adapter.py",
    ],
    "2B-15 Face Reaction Analysis": [
        "models/face_reaction_analysis.py",
        "core/face_reaction_analyzer.py",
        "models/face_reaction_source.py",
        "models/face_reaction_run.py",
        "core/face_reaction_source_selector.py",
        "core/face_reaction_runner.py",
        "core/face_reaction_signal_adapter.py",
    ],
    "2B-16 Stutter / Duplicate Detection": [
        "models/stutter_detection.py",
        "core/stutter_detector.py",
        "models/stutter_detection_source.py",
        "models/stutter_detection_run.py",
        "core/stutter_detection_source_selector.py",
        "core/stutter_detection_runner.py",
        "core/stutter_detection_signal_adapter.py",
    ],
    "2B-17 Screen Content Classifier": [
        "models/screen_content_classification.py",
        "core/screen_content_classifier.py",
        "models/screen_content_source.py",
        "models/screen_content_run.py",
        "core/screen_content_source_selector.py",
        "core/screen_content_runner.py",
        "core/screen_content_signal_adapter.py",
    ],
    "2B-18 Visual Energy Score": [
        "models/visual_energy.py",
        "core/visual_energy_calculator.py",
        "models/visual_energy_run.py",
        "core/visual_energy_runner.py",
        "core/visual_energy_signal_adapter.py",
    ],
}


FINAL_AUDIT_TEST_FILES = [
    "tests/test_scene_change_final_audit_smoke.py",
    "tests/test_motion_analysis_final_audit_smoke.py",
    "tests/test_face_reaction_final_audit_smoke.py",
    "tests/test_stutter_detection_final_audit_smoke.py",
    "tests/test_screen_content_final_audit_smoke.py",
    "tests/test_visual_energy_final_audit_smoke.py",
]


PIPELINE_BLOCK_MARKERS = [
    "Scene Change Detection",
    "Motion Analysis",
    "Face Reaction Analysis",
    "Stutter Detection",
    "Screen Content Classification",
    "Visual Energy Score",
]


PIPELINE_CHECKPOINTS = [
    "scene_change_done",
    "motion_analysis_done",
    "face_reaction_done",
    "stutter_detection_done",
    "screen_content_done",
    "visual_energy_done",
]


REGISTRY_SOURCES = [
    "scene_change",
    "motion_analysis",
    "face_reaction",
    "stutter_detection",
    "screen_content",
    "visual_energy",
]


FILES_THAT_MUST_BE_CLEAN_TEXT = [
    "tests/test_block3_video_intelligence_static_audit_smoke.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
]


def _path(relative_path: str) -> Path:
    return REPO_ROOT / relative_path


def _read_text(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_all_block3_implementation_files_exist() -> None:
    missing_files: list[str] = []

    for group_name, relative_paths in BLOCK3_IMPLEMENTATION_FILES.items():
        for relative_path in relative_paths:
            if not _path(relative_path).is_file():
                missing_files.append(f"{group_name}: {relative_path}")

    assert not missing_files, "Missing Block 3 files:\n" + "\n".join(missing_files)


def test_all_block3_final_audit_tests_exist() -> None:
    missing_files = [
        relative_path
        for relative_path in FINAL_AUDIT_TEST_FILES
        if not _path(relative_path).is_file()
    ]

    assert not missing_files, "Missing final audit tests:\n" + "\n".join(missing_files)


def test_gaming_pipeline_contains_all_block3_blocks() -> None:
    text = _read_text("core/gaming_pipeline.py")

    missing_markers = [
        marker
        for marker in PIPELINE_BLOCK_MARKERS
        if marker not in text
    ]

    assert not missing_markers, (
        "Missing Block 3 pipeline markers:\n" + "\n".join(missing_markers)
    )


def test_gaming_pipeline_contains_all_block3_checkpoints() -> None:
    text = _read_text("core/gaming_pipeline.py")

    missing_checkpoints = [
        checkpoint
        for checkpoint in PIPELINE_CHECKPOINTS
        if checkpoint not in text
    ]

    assert not missing_checkpoints, (
        "Missing Block 3 pipeline checkpoints:\n"
        + "\n".join(missing_checkpoints)
    )


def test_unified_registry_contains_all_block3_sources() -> None:
    text = _read_text("core/unified_edit_signal_registry.py")

    missing_sources = [
        source
        for source in REGISTRY_SOURCES
        if f'"{source}"' not in text and f"'{source}'" not in text
    ]

    assert not missing_sources, (
        "Missing Block 3 registry sources:\n" + "\n".join(missing_sources)
    )


def test_static_audit_files_have_no_bom_and_end_with_newline() -> None:
    broken_files: list[str] = []

    for relative_path in FILES_THAT_MUST_BE_CLEAN_TEXT:
        content = _path(relative_path).read_bytes()

        if content.startswith(b"\xef\xbb\xbf"):
            broken_files.append(f"{relative_path}: has UTF-8 BOM")

        if not content.endswith(b"\n"):
            broken_files.append(f"{relative_path}: does not end with newline")

    assert not broken_files, "Text hygiene problems:\n" + "\n".join(broken_files)
