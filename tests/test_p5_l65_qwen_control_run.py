from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "p5_l65_qwen_control_run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("p5_l65_qwen_control_run", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def out_dir(repo: Path) -> Path:
    return repo / "reports" / "p5_l65_qwen_control_run"


def test_script_importable() -> None:
    module = load_module()
    assert module.PHASE == "P5-L6.5"
    assert module.GROUP == "5D"
    assert module.MODE == "qwen_control_run"


def test_default_without_qwen_writes_plan_and_safety_false(tmp_path: Path) -> None:
    module = load_module()
    repo = tmp_path / "repo"

    result = module.run_control(repo_root=repo, output_dir=out_dir(repo))
    manifest = result["manifest"]

    assert manifest["status"] == "planned_without_qwen"
    assert manifest["qwen_requested"] is False
    assert manifest["qwen_used"] is False
    assert manifest["qwen_visible_response"] is False

    expected_false = [
        "render_used",
        "ingest_used",
        "music_used",
        "autocut_used",
        "timeline_modified",
        "learning_loop_started",
        "overnight_started",
        "real_overnight_started",
        "phase_5_5_used",
        "external_network_used",
        "api_key_used",
        "production_files_modified",
        "video_configs_modified",
        "learning_corpus_modified",
        "obsidian_modified_by_script",
        "core_modified",
        "dangerous_response_detected",
    ]

    for key in expected_false:
        assert manifest[key] is False


def test_fake_safe_qwen_response_is_visible_and_safe(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    repo = tmp_path / "repo"

    def fake_qwen(repo_root, manifest, model, base_url, timeout_sec):
        payload = {
            "role": "analysis_only",
            "can_cut": False,
            "action": "analyze",
            "summary": "ok",
            "risks": [],
            "recommendation": "continue guarded",
            "owner_review_required": True,
        }
        normalized = module.normalize_qwen_payload(payload)
        response = {"status": "ok", "visible_response": True, "payload": payload}
        module.apply_normalized_response(manifest, response, normalized)
        return response

    monkeypatch.setattr(module, "run_local_qwen_control", fake_qwen)
    result = module.run_control(
        repo_root=repo,
        output_dir=out_dir(repo),
        enable_local_qwen=True,
        model="qwen-test",
    )
    manifest = result["manifest"]

    assert manifest["qwen_used"] is True
    assert manifest["qwen_visible_response"] is True
    assert manifest["qwen_can_cut"] is False
    assert manifest["dangerous_response_detected"] is False


def test_dangerous_qwen_response_is_no_go_without_execution(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    repo = tmp_path / "repo"

    def fake_qwen(repo_root, manifest, model, base_url, timeout_sec):
        payload = {
            "role": "analysis_only",
            "can_cut": True,
            "action": "cut",
        }
        normalized = module.normalize_qwen_payload(payload)
        response = {"status": "no_go", "visible_response": True, "payload": payload}
        module.apply_normalized_response(manifest, response, normalized)
        return response

    monkeypatch.setattr(module, "run_local_qwen_control", fake_qwen)
    result = module.run_control(
        repo_root=repo,
        output_dir=out_dir(repo),
        enable_local_qwen=True,
        model="qwen-test",
    )
    manifest = result["manifest"]

    assert manifest["status"] == "no_go"
    assert manifest["dangerous_response_detected"] is True
    assert manifest["autocut_used"] is False
    assert manifest["render_used"] is False
    assert manifest["timeline_modified"] is False


def test_external_url_blocked_and_local_allowed() -> None:
    module = load_module()

    with pytest.raises(ValueError):
        module.validate_local_base_url("http://example.com")

    assert module.validate_local_base_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert module.validate_local_base_url("http://localhost:11434") == "http://localhost:11434"


def test_output_scope_only_allowed_report_dir(tmp_path: Path) -> None:
    module = load_module()
    repo = tmp_path / "repo"

    result = module.run_control(repo_root=repo, output_dir=out_dir(repo))
    manifest = result["manifest"]

    assert manifest["writes_only_under"] == "reports/p5_l65_qwen_control_run"
    assert sorted(manifest["outputs_written"]) == [
        "reports/p5_l65_qwen_control_run/qwen_control_manifest.json",
        "reports/p5_l65_qwen_control_run/qwen_control_response.json",
        "reports/p5_l65_qwen_control_run/qwen_control_summary.md",
    ]
    assert not (repo / "video_configs").exists()
    assert not (repo / "learning_corpus").exists()
    assert not (repo / "core").exists()
    assert not (repo / "obsidian_zenith").exists()

    with pytest.raises(ValueError):
        module.run_control(repo_root=repo, output_dir=repo / "reports" / "other")


def test_timeout_fail_closed(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    repo = tmp_path / "repo"

    def fake_qwen(repo_root, manifest, model, base_url, timeout_sec):
        manifest["status"] = "qwen_timeout"
        manifest["qwen_requested"] = True
        manifest["qwen_used"] = False
        manifest["qwen_visible_response"] = False
        return {"status": "qwen_timeout", "visible_response": False}

    monkeypatch.setattr(module, "run_local_qwen_control", fake_qwen)
    result = module.run_control(
        repo_root=repo,
        output_dir=out_dir(repo),
        enable_local_qwen=True,
        model="qwen-test",
    )
    manifest = result["manifest"]

    assert manifest["status"] == "qwen_timeout"
    assert manifest["qwen_used"] is False
    assert manifest["qwen_visible_response"] is False


def test_forbidden_imports_and_usage_not_in_script() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8").lower()

    forbidden = [
        "sub" + "process",
        "req" + "uests",
        "ff" + "mpeg",
        "whis" + "per",
        "render" + "_short",
        "shutil." + "rm" + "tree",
        "os." + "remove",
        "." + "un" + "link(",
        "while " + "true",
    ]

    for needle in forbidden:
        assert needle not in text

    assert "urllib.parse" in text
    assert "127.0.0.1" in text
    assert "localhost" in text
