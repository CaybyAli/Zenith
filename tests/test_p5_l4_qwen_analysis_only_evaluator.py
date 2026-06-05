from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "p5_l4_qwen_analysis_only_evaluator.py"


def load_module():
    spec = importlib.util.spec_from_file_location("p5_l4_qwen_analysis_only_evaluator", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_repo(tmp_path: Path, with_candidate: bool = True, with_manifest: bool = True) -> Path:
    repo = tmp_path / "repo"
    p5_l3 = repo / "reports" / "p5_l3_style_memory_safe_write"
    p5_l2 = repo / "reports" / "p5_l2_analysis_only_dry_run"
    p5_l3.mkdir(parents=True)
    p5_l2.mkdir(parents=True)

    if with_candidate:
        (p5_l3 / "style_memory_candidate.json").write_text(
            json.dumps(
                {
                    "candidate_only": True,
                    "memory_write_target": "reports_only_candidate",
                    "can_be_used_for_production": False,
                    "owner_review_required": True,
                }
            ),
            encoding="utf-8",
        )

    if with_manifest:
        (p5_l3 / "style_memory_manifest.json").write_text(
            json.dumps(
                {
                    "status": "ok",
                    "memory_write_target": "reports_only_candidate",
                    "can_be_used_for_production": False,
                    "owner_review_required": True,
                }
            ),
            encoding="utf-8",
        )

    (p5_l2 / "p5_l2_analysis_report.json").write_text(
        json.dumps({"status": "ok", "mode": "analysis_only_dry_run"}),
        encoding="utf-8",
    )

    return repo


def output_dir(repo: Path) -> Path:
    return repo / "reports" / "p5_l4_qwen_analysis_only_evaluator"


def test_script_importable() -> None:
    module = load_module()
    assert module.PHASE == "P5-L4"
    assert module.MODE == "qwen_analysis_only_evaluator"


def test_script_has_no_forbidden_operational_usage() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8").lower()

    forbidden = [
        "sub" + "process",
        "req" + "uests",
        "ollama import",
        "ff" + "mpeg",
        "whis" + "per",
        "render" + "_short",
        "shutil." + "rm" + "tree",
        "os." + "remove",
        "." + "un" + "link(",
    ]

    for needle in forbidden:
        assert needle not in text

    assert "urllib.parse" in text
    assert "127.0.0.1" in text
    assert "localhost" in text
    assert "allowed_local_hosts" in text


def test_fake_repo_default_run_writes_outputs(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(tmp_path)

    report = module.run_evaluator(
        repo_root=repo,
        output_dir=output_dir(repo),
    )

    assert report["status"] == "ok"
    assert (output_dir(repo) / "qwen_analysis_report.json").exists()
    assert (output_dir(repo) / "qwen_analysis_manifest.json").exists()
    assert (output_dir(repo) / "qwen_analysis_summary.md").exists()


def test_safety_flags_default_run(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(tmp_path)

    report = module.run_evaluator(
        repo_root=repo,
        output_dir=output_dir(repo),
    )

    expected_false = [
        "qwen_requested",
        "qwen_used",
        "qwen_can_cut",
        "qwen_autocut_allowed",
        "external_network_used",
        "api_key_used",
        "render_used",
        "ingest_used",
        "music_used",
        "autocut_used",
        "overnight_started",
        "learning_loop_started",
        "phase_5_5_used",
        "timeline_modified",
        "production_files_modified",
        "video_configs_modified",
        "learning_corpus_modified",
        "obsidian_modified_by_script",
        "core_modified",
        "dangerous_response_detected",
    ]

    for key in expected_false:
        assert report[key] is False

    assert report["qwen_role"] == "analysis_only"
    assert report["deleted_files"] == []


def test_output_scope_only_allowed_reports_folder(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(tmp_path)

    report = module.run_evaluator(
        repo_root=repo,
        output_dir=output_dir(repo),
    )

    assert report["writes_only_under"] == "reports/p5_l4_qwen_analysis_only_evaluator"
    assert sorted(report["outputs_written"]) == [
        "reports/p5_l4_qwen_analysis_only_evaluator/qwen_analysis_manifest.json",
        "reports/p5_l4_qwen_analysis_only_evaluator/qwen_analysis_report.json",
        "reports/p5_l4_qwen_analysis_only_evaluator/qwen_analysis_summary.md",
    ]

    assert not (repo / "video_configs").exists()
    assert not (repo / "learning_corpus").exists()
    assert not (repo / "obsidian_zenith").exists()
    assert not (repo / "core").exists()


def test_missing_p5_l3_candidate_returns_error(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(tmp_path, with_candidate=False)

    report = module.run_evaluator(
        repo_root=repo,
        output_dir=output_dir(repo),
    )

    assert report["status"] == "error"
    assert "style_memory_candidate.json" in report["warnings"][0]


def test_missing_p5_l3_manifest_returns_error(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(tmp_path, with_manifest=False)

    report = module.run_evaluator(
        repo_root=repo,
        output_dir=output_dir(repo),
    )

    assert report["status"] == "error"
    assert "style_memory_manifest.json" in report["warnings"][0]


def test_output_outside_allowed_folder_is_blocked(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(tmp_path)

    with pytest.raises(ValueError):
        module.run_evaluator(
            repo_root=repo,
            output_dir=repo / "reports" / "wrong_folder",
        )


def test_qwen_dangerous_response_is_no_go_and_executes_nothing() -> None:
    module = load_module()

    normalized = module.normalize_qwen_payload(
        {
            "role": "analysis_only",
            "can_cut": True,
            "action": "cut",
        }
    )

    assert normalized["status"] == "no_go"
    assert normalized["dangerous_response_detected"] is True
    assert normalized["autocut_used"] is False
    assert normalized["render_used"] is False
    assert normalized["ingest_used"] is False
    assert normalized["music_used"] is False
    assert normalized["timeline_modified"] is False


def test_external_url_blocked_and_local_urls_allowed() -> None:
    module = load_module()

    with pytest.raises(ValueError):
        module.validate_local_qwen_base_url("https://example.com")

    with pytest.raises(ValueError):
        module.validate_local_qwen_base_url("http://example.com")

    assert module.validate_local_qwen_base_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert module.validate_local_qwen_base_url("http://localhost:11434") == "http://localhost:11434"
