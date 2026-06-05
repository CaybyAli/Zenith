from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "p5_l5_overnight_dry_run.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("p5_l5_overnight_dry_run", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_fake_repo(repo: Path) -> None:
    _write_json(
        repo / "reports" / "p5_l2_analysis_only_dry_run" / "p5_l2_analysis_report.json",
        {"status": "ok", "mode": "analysis_only_dry_run"},
    )
    _write_json(
        repo / "reports" / "p5_l3_style_memory_safe_write" / "style_memory_candidate.json",
        {"status": "ok", "memory_write_target": "reports_only_candidate"},
    )
    _write_json(
        repo / "reports" / "p5_l3_style_memory_safe_write" / "style_memory_manifest.json",
        {"status": "ok", "can_be_used_for_production": False},
    )
    _write_json(
        repo / "reports" / "p5_l4_qwen_analysis_only_evaluator" / "qwen_analysis_manifest.json",
        {"status": "ok", "qwen_role": "analysis_only", "qwen_can_cut": False},
    )
    _write_json(
        repo / "reports" / "p5_l4_qwen_analysis_only_evaluator" / "qwen_analysis_report.json",
        {"status": "ok", "qwen_used": False},
    )

    _write_json(
        repo / "learning_corpus" / "pairs" / "pair_001" / "style_fingerprint.json",
        {"style": "pair_safe", "source": "style_fingerprint_only"},
    )
    _write_json(
        repo / "learning_corpus" / "top_solo" / "solo_001" / "style_fingerprint.json",
        {"style": "solo_safe", "source": "style_fingerprint_only"},
    )
    _write_json(
        repo / "learning_corpus" / "vlogs" / "vlog_001" / "style_fingerprint.json",
        {"style": "vlog_safe", "source": "style_fingerprint_only"},
    )


def test_script_importable():
    module = _load_module()
    assert hasattr(module, "run_overnight_dry_run")


def test_forbidden_imports_and_real_usage_are_absent():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    forbidden_real_usage = [
        "import " + "sub" + "process",
        "from " + "sub" + "process",
        "sub" + "process.",
        "import " + "re" + "quests",
        "from " + "re" + "quests",
        "re" + "quests.",
        "import " + "ur" + "llib",
        "from " + "ur" + "llib",
        "ur" + "llib.",
        "import " + "ol" + "lama",
        "ol" + "lama.",
        "import " + "ff" + "mpeg",
        "ff" + "mpeg.",
        "import " + "whi" + "sper",
        "whi" + "sper.",
        "render" + "_short",
        "shutil." + "rm" + "tree",
        "os." + "re" + "move",
        "." + "un" + "link(",
        "while" + " " + "True",
    ]
    for needle in forbidden_real_usage:
        assert needle not in text

def test_fake_repo_run_writes_outputs_and_plans_three_items(tmp_path: Path):
    module = _load_module()
    _make_fake_repo(tmp_path)

    result = module.run_overnight_dry_run(
        repo_root=tmp_path,
        output_dir=Path("reports") / "p5_l5_overnight_dry_run",
        max_items=3,
    )

    manifest = result["manifest"]
    plan = result["plan"]

    assert manifest["status"] == "ok"
    assert manifest["items_planned"] == 3
    assert manifest["items_processed"] == 3
    assert len(plan["planned_items"]) == 3

    for rel_path in manifest["outputs_written"]:
        output_path = tmp_path / rel_path
        assert output_path.exists()


def test_safety_flags_stay_false(tmp_path: Path):
    module = _load_module()
    _make_fake_repo(tmp_path)

    manifest = module.run_overnight_dry_run(
        repo_root=tmp_path,
        output_dir=Path("reports") / "p5_l5_overnight_dry_run",
        max_items=3,
    )["manifest"]

    assert manifest["dry_run_only"] is True
    assert manifest["real_overnight_started"] is False
    assert manifest["overnight_started"] is False
    assert manifest["bounded_run"] is True
    assert manifest["qwen_used"] is False
    assert manifest["qwen_autocut_used"] is False
    assert manifest["render_used"] is False
    assert manifest["ingest_used"] is False
    assert manifest["music_used"] is False
    assert manifest["autocut_used"] is False
    assert manifest["learning_loop_started"] is False
    assert manifest["phase_5_5_used"] is False
    assert manifest["external_network_used"] is False
    assert manifest["api_key_used"] is False
    assert manifest["production_files_modified"] is False
    assert manifest["video_configs_modified"] is False
    assert manifest["learning_corpus_modified"] is False
    assert manifest["obsidian_modified_by_script"] is False
    assert manifest["core_modified"] is False
    assert manifest["deleted_files"] == []


def test_output_scope_only_allowed_report_folder(tmp_path: Path):
    module = _load_module()
    _make_fake_repo(tmp_path)

    manifest = module.run_overnight_dry_run(
        repo_root=tmp_path,
        output_dir=Path("reports") / "p5_l5_overnight_dry_run",
        max_items=3,
    )["manifest"]

    assert manifest["writes_only_under"] == "reports/p5_l5_overnight_dry_run"
    for rel_path in manifest["outputs_written"]:
        assert rel_path.startswith("reports/p5_l5_overnight_dry_run/")
        assert (tmp_path / rel_path).exists()

    assert not (tmp_path / "video_configs").exists()
    assert not (tmp_path / "obsidian_zenith").exists()
    assert not (tmp_path / "core").exists()


def test_max_items_guard(tmp_path: Path):
    module = _load_module()
    _make_fake_repo(tmp_path)

    with pytest.raises(ValueError):
        module.run_overnight_dry_run(
            repo_root=tmp_path,
            output_dir=Path("reports") / "p5_l5_overnight_dry_run",
            max_items=11,
        )

    manifest = module.run_overnight_dry_run(
        repo_root=tmp_path,
        output_dir=Path("reports") / "p5_l5_overnight_dry_run",
        max_items=5,
    )["manifest"]
    assert manifest["max_items"] == 5
    assert manifest["items_planned"] <= 5


def test_stop_file_stops_cleanly(tmp_path: Path):
    module = _load_module()
    _make_fake_repo(tmp_path)

    out = tmp_path / "reports" / "p5_l5_overnight_dry_run"
    out.mkdir(parents=True, exist_ok=True)
    (out / "STOP").write_text("stop", encoding="utf-8")

    manifest = module.run_overnight_dry_run(
        repo_root=tmp_path,
        output_dir=Path("reports") / "p5_l5_overnight_dry_run",
        max_items=5,
    )["manifest"]

    assert manifest["status"] == "stopped_by_stop_file"
    assert manifest["stop_file_detected"] is True
    assert manifest["items_planned"] == 0
    assert manifest["items_processed"] == 0
    assert manifest["qwen_used"] is False
    assert manifest["render_used"] is False
    assert manifest["ingest_used"] is False
    assert manifest["music_used"] is False


def test_output_outside_allowed_folder_errors(tmp_path: Path):
    module = _load_module()
    _make_fake_repo(tmp_path)

    with pytest.raises(ValueError):
        module.run_overnight_dry_run(
            repo_root=tmp_path,
            output_dir=Path("reports") / "not_allowed",
            max_items=3,
        )


def test_ali_voice_reference_input_is_forbidden(tmp_path: Path):
    module = _load_module()
    _make_fake_repo(tmp_path)
    _write_json(
        tmp_path / "learning_corpus" / "pairs" / "pair_002" / "style_fingerprint.json",
        {"style": "bad", "voice_source": "ali_voice_reference.wav"},
    )

    manifest = module.run_overnight_dry_run(
        repo_root=tmp_path,
        output_dir=Path("reports") / "p5_l5_overnight_dry_run",
        max_items=5,
    )["manifest"]

    assert manifest["status"] == "blocked_for_forbidden_input"
    assert manifest["forbidden_inputs_used"]
