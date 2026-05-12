from __future__ import annotations

from pathlib import Path


FILES_2B13_A = [
    Path("models/scene_change.py"),
    Path("core/scene_change_detector.py"),
    Path("tests/test_scene_change_detection_foundation_smoke.py"),
]

FILES_2B13_B = [
    Path("models/scene_change_source.py"),
    Path("models/scene_change_run.py"),
    Path("core/scene_change_source_selector.py"),
    Path("core/scene_change_runner.py"),
    Path("tests/test_scene_change_source_selector_smoke.py"),
    Path("tests/test_scene_change_runner_smoke.py"),
]

FILES_2B13_C = [
    Path("tests/test_scene_change_pipeline_integration_smoke.py"),
]

FILES_2B13_D = [
    Path("core/scene_change_signal_adapter.py"),
    Path("tests/test_scene_change_signal_adapter_smoke.py"),
]

FILES_2B13_E = [
    Path("tests/test_scene_change_registry_integration_smoke.py"),
    Path("tests/test_scene_change_final_audit_smoke.py"),
]

GAMING_PIPELINE_PATH = Path("core/gaming_pipeline.py")
REGISTRY_PATH = Path("core/unified_edit_signal_registry.py")
ADAPTER_PATH = Path("core/scene_change_signal_adapter.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_all_2b13_files_exist() -> None:
    all_paths = (
        FILES_2B13_A
        + FILES_2B13_B
        + FILES_2B13_C
        + FILES_2B13_D
        + FILES_2B13_E
        + [GAMING_PIPELINE_PATH, REGISTRY_PATH, ADAPTER_PATH]
    )

    missing = [str(path) for path in all_paths if not path.exists()]
    assert not missing, f"Missing 2B-13 files: {missing}"


def test_2b13_a_foundation_files_exist() -> None:
    for path in FILES_2B13_A:
        assert path.exists(), f"Missing 2B-13-A file: {path}"


def test_2b13_b_runner_files_exist() -> None:
    for path in FILES_2B13_B:
        assert path.exists(), f"Missing 2B-13-B file: {path}"


def test_2b13_c_pipeline_block_exists() -> None:
    content = _read(GAMING_PIPELINE_PATH)

    assert "Scene Change Detection (2B-13-C)" in content
    assert "run_scene_change_for_job" in content
    assert "apply_scene_change_run_report_to_job" in content
    assert "SCENE_CHANGE_STARTED" in content
    assert "SCENE_CHANGE_DONE" in content
    assert "SCENE_CHANGE_FAILED" in content
    assert 'step_name="scene_change_done"' in content


def test_2b13_d_adapter_exists_and_maps_scene_changes() -> None:
    content = _read(ADAPTER_PATH)

    assert "adapt_scene_change_report_to_signals" in content
    assert "adapt_scene_changes_to_signals" in content
    assert "build_scene_change_signal" in content
    assert "scene_hard_cut_point" in content
    assert "scene_soft_transition" in content
    assert "scene_flash_or_explosion_candidate" in content
    assert "review_false_positive_scene_change" in content


def test_2b13_e_registry_imports_and_collects_scene_change() -> None:
    content = _read(REGISTRY_PATH)

    assert "from core.scene_change_signal_adapter import adapt_scene_change_report_to_signals" in content
    assert 'SOURCE_SCENE_CHANGE = "scene_change"' in content
    assert 'scene_change_report = _job_attr(job, "scene_change_report")' in content
    assert 'scene_changes = _job_attr(job, "scene_changes")' in content
    assert "adapt_scene_change_report_to_signals(scene_change_report)" in content
    assert "source_counts[SOURCE_SCENE_CHANGE]" in content
    assert "_normalize_signal(signal, SOURCE_SCENE_CHANGE)" in content


def test_flash_explosion_remains_review_signal_not_cut_boundary() -> None:
    content = _read(ADAPTER_PATH)

    assert "flash_or_explosion_candidate" in content
    assert "scene_flash_or_explosion_candidate" in content
    assert "review_false_positive_scene_change" in content

    flash_block_start = content.index("if change_type == CHANGE_TYPE_FLASH:")
    flash_block_end = content.index(
        '    return {\n        "signal_type": "scene_unknown_change"',
        flash_block_start,
    )
    flash_block = content[flash_block_start:flash_block_end]

    assert "SIGNAL_TYPE_FLASH" in flash_block
    assert "review_false_positive_scene_change" in flash_block
    assert "candidate_cut_boundary" not in flash_block


def test_all_scene_change_tests_exist() -> None:
    test_paths = [
        Path("tests/test_scene_change_detection_foundation_smoke.py"),
        Path("tests/test_scene_change_source_selector_smoke.py"),
        Path("tests/test_scene_change_runner_smoke.py"),
        Path("tests/test_scene_change_pipeline_integration_smoke.py"),
        Path("tests/test_scene_change_signal_adapter_smoke.py"),
        Path("tests/test_scene_change_registry_integration_smoke.py"),
        Path("tests/test_scene_change_final_audit_smoke.py"),
    ]

    for path in test_paths:
        assert path.exists(), f"Missing scene change test: {path}"


def test_scene_change_final_audit_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        GAMING_PIPELINE_PATH,
        REGISTRY_PATH,
        ADAPTER_PATH,
        Path("tests/test_scene_change_registry_integration_smoke.py"),
        Path("tests/test_scene_change_final_audit_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
