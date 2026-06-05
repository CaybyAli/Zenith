from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "p5_l6_owner_review_quality_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("p5_l6_owner_review_quality_gate", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def make_fake_repo(tmp_path: Path, include_l3_manifest: bool = True, include_l5_manifest: bool = True) -> Path:
    repo = tmp_path / "repo"

    write_json(
        repo / "reports/p5_l2_analysis_only_dry_run/p5_l2_analysis_report.json",
        {
            "status": "ok",
            "phase": "P5-L2",
            "mode": "analysis_only_dry_run",
            "qwen_used": False,
            "render_used": False,
            "ingest_used": False,
            "music_used": False,
            "autocut_used": False,
            "learning_loop_started": False,
            "phase_5_5_used": False,
            "deleted_files": [],
            "counts": {
                "pair_fingerprints": 20,
                "top_solo_fingerprints": 30,
                "vlog_fingerprints": 3,
                "pair_truth_entries": 20,
            },
            "forbidden_inputs_used": [],
            "warnings": [],
        },
    )

    if include_l3_manifest:
        write_json(
            repo / "reports/p5_l3_style_memory_safe_write/style_memory_manifest.json",
            {
                "status": "ok",
                "phase": "P5-L3",
                "memory_write_target": "reports_only_candidate",
                "production_files_modified": False,
                "video_configs_modified": False,
                "learning_corpus_modified": False,
                "obsidian_modified_by_script": False,
                "core_modified": False,
                "qwen_used": False,
                "render_used": False,
                "ingest_used": False,
                "music_used": False,
                "autocut_used": False,
                "overnight_started": False,
                "learning_loop_started": False,
                "phase_5_5_used": False,
                "deleted_files": [],
                "forbidden_inputs_used": [],
                "warnings": [],
            },
        )

    write_json(
        repo / "reports/p5_l3_style_memory_safe_write/style_memory_candidate.json",
        {
            "candidate_only": True,
            "can_be_used_for_production": False,
            "owner_review_required": True,
        },
    )

    write_json(
        repo / "reports/p5_l4_qwen_analysis_only_evaluator/qwen_analysis_manifest.json",
        {
            "status": "ok",
            "phase": "P5-L4",
            "qwen_requested": True,
            "qwen_used": False,
            "qwen_role": "analysis_only",
            "qwen_can_cut": False,
            "qwen_autocut_allowed": False,
            "dangerous_response_detected": False,
            "render_used": False,
            "ingest_used": False,
            "music_used": False,
            "autocut_used": False,
            "overnight_started": False,
            "learning_loop_started": False,
            "phase_5_5_used": False,
            "timeline_modified": False,
            "production_files_modified": False,
            "video_configs_modified": False,
            "learning_corpus_modified": False,
            "obsidian_modified_by_script": False,
            "core_modified": False,
            "deleted_files": [],
            "local_qwen_status": "skipped_import_unavailable",
            "warnings": [],
            "forbidden_inputs_used": [],
        },
    )

    if include_l5_manifest:
        write_json(
            repo / "reports/p5_l5_overnight_dry_run/overnight_dry_run_manifest.json",
            {
                "status": "ok",
                "phase": "P5-L5",
                "mode": "overnight_dry_run",
                "dry_run_only": True,
                "real_overnight_started": False,
                "overnight_started": False,
                "bounded_run": True,
                "max_items": 5,
                "items_planned": 5,
                "items_processed": 5,
                "qwen_used": False,
                "qwen_autocut_used": False,
                "render_used": False,
                "ingest_used": False,
                "music_used": False,
                "autocut_used": False,
                "learning_loop_started": False,
                "phase_5_5_used": False,
                "external_network_used": False,
                "api_key_used": False,
                "production_files_modified": False,
                "video_configs_modified": False,
                "learning_corpus_modified": False,
                "obsidian_modified_by_script": False,
                "core_modified": False,
                "deleted_files": [],
                "warnings": [],
                "forbidden_inputs_used": [],
            },
        )

    write_json(
        repo / "reports/p5_l5_overnight_dry_run/overnight_dry_run_plan.json",
        {
            "planned_items": [
                {"item_id": "pair_001", "action": "analysis_planning_only"},
                {"item_id": "pair_002", "action": "analysis_planning_only"},
            ]
        },
    )

    return repo


def test_script_importable():
    module = load_module()
    assert hasattr(module, "build_owner_review")
    assert hasattr(module, "validate_local_qwen_base_url")


def test_fake_repo_without_qwen_writes_outputs(tmp_path):
    module = load_module()
    repo = make_fake_repo(tmp_path)
    out = repo / "reports/p5_l6_owner_review_quality_gate"

    manifest = module.build_owner_review(repo, "reports/p5_l6_owner_review_quality_gate")

    assert manifest["status"] == "ok"
    assert (out / "owner_review_packet.json").exists()
    assert (out / "owner_review_manifest.json").exists()
    assert (out / "owner_review_summary.md").exists()
    assert (out / "qwen_wake_up_response.json").exists()


def test_safety_flags_without_qwen(tmp_path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    manifest = module.build_owner_review(repo, "reports/p5_l6_owner_review_quality_gate")

    expected_false = [
        "qwen_requested",
        "qwen_used",
        "qwen_can_cut",
        "qwen_autocut_allowed",
        "render_used",
        "ingest_used",
        "music_used",
        "autocut_used",
        "overnight_started",
        "real_overnight_started",
        "learning_loop_started",
        "phase_5_5_used",
        "external_network_used",
        "api_key_used",
        "timeline_modified",
        "production_files_modified",
        "video_configs_modified",
        "learning_corpus_modified",
        "obsidian_modified_by_script",
        "core_modified",
    ]

    for key in expected_false:
        assert manifest[key] is False

    assert manifest["qwen_role"] == "analysis_only"
    assert manifest["deleted_files"] == []
    assert manifest["owner_review_required"] is True
    assert manifest["owner_review_completed"] is False
    assert manifest["owner_go"] is False
    assert manifest["owner_review_source"] is None


def test_owner_review_go_marks_manifest_machine_readable(tmp_path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    manifest = module.build_owner_review(
        repo,
        "reports/p5_l6_owner_review_quality_gate",
        owner_review_go=True,
    )

    assert manifest["status"] == "ok"
    assert manifest["owner_review_required"] is True
    assert manifest["owner_review_completed"] is True
    assert manifest["owner_go"] is True
    assert manifest["owner_review_source"] == "ali_manual_owner_review"

    owner_finding = [
        item
        for item in manifest["quality_findings"]
        if item["area"] == "P5-L6 owner review requirement"
    ][0]
    assert owner_finding["status"] == "completed"
    assert owner_finding["evidence"]["owner_review_completed"] is True
    assert owner_finding["evidence"]["owner_go"] is True


def test_output_scope_only_reports_p5_l6(tmp_path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    manifest = module.build_owner_review(repo, "reports/p5_l6_owner_review_quality_gate")

    assert manifest["writes_only_under"] == "reports/p5_l6_owner_review_quality_gate"
    for rel_path in manifest["outputs_written"]:
        assert rel_path.startswith("reports/p5_l6_owner_review_quality_gate/")

    assert not (repo / "video_configs").exists()
    assert not (repo / "learning_corpus").exists()
    assert not (repo / "obsidian_zenith").exists()
    assert not (repo / "core").exists()


def test_missing_p5_l3_or_p5_l5_report_returns_error(tmp_path):
    module = load_module()

    repo_missing_l3 = make_fake_repo(tmp_path / "a", include_l3_manifest=False)
    manifest_l3 = module.build_owner_review(repo_missing_l3, "reports/p5_l6_owner_review_quality_gate")
    assert manifest_l3["status"] == "error"
    assert manifest_l3["quality_gate_ready"] is False

    repo_missing_l5 = make_fake_repo(tmp_path / "b", include_l5_manifest=False)
    manifest_l5 = module.build_owner_review(repo_missing_l5, "reports/p5_l6_owner_review_quality_gate")
    assert manifest_l5["status"] == "error"
    assert manifest_l5["quality_gate_ready"] is False


def test_external_url_blocked_and_local_allowed():
    module = load_module()

    with pytest.raises(ValueError):
        module.validate_local_qwen_base_url("https://example.com")

    with pytest.raises(ValueError):
        module.validate_local_qwen_base_url("http://192.168.1.5:11434")

    assert module.validate_local_qwen_base_url("http://127.0.0.1:11434") == "http://127.0.0.1:11434"
    assert module.validate_local_qwen_base_url("http://localhost:11434") == "http://localhost:11434"


def test_dangerous_qwen_response_no_go_without_execution(tmp_path, monkeypatch):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    def fake_local_qwen(base_url, model, prompt, timeout_seconds=8):
        return {
            "status": "ok",
            "qwen_requested": True,
            "qwen_used": True,
            "warning": "",
            "raw_response": "",
            "payload": {
                "role": "analysis_only",
                "can_cut": True,
                "action": "cut",
                "recommendation_text": "bad",
                "risks": [],
                "owner_review_required": True,
            },
        }

    monkeypatch.setattr(module, "run_local_qwen", fake_local_qwen)

    manifest = module.build_owner_review(
        repo,
        "reports/p5_l6_owner_review_quality_gate",
        enable_local_qwen=True,
    )

    assert manifest["status"] == "no_go"
    assert manifest["dangerous_response_detected"] is True
    assert manifest["autocut_used"] is False
    assert manifest["render_used"] is False
    assert manifest["ingest_used"] is False
    assert manifest["music_used"] is False


def test_forbidden_imports_and_usage_not_in_script():
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    forbidden = [
        "sub" + "process",
        "request" + "s",
        "ff" + "mpeg",
        "whis" + "per",
        "render_" + "short",
        "Remove" + "-Item",
        "rm" + "tree",
        "un" + "link",
        "os." + "remove",
        "while " + "True",
        "git add " + "-A",
        "git add " + ".",
        "api/" + "generate",
    ]

    for token in forbidden:
        assert token not in source
