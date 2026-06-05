from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "p5_l2_analysis_only_dry_run.py"


def load_module():
    spec = importlib.util.spec_from_file_location("p5_l2_analysis_only_dry_run", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def make_fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"

    write_json(repo / "video_configs" / "gaming_pairs_style_dna.json", {"style": {"cuts": 3}})
    write_json(repo / "video_configs" / "top_solo_style_dna.json", {"style": {"cuts": 2}})
    write_json(repo / "video_configs" / "vlog_style_dna.json", {"style": {"cuts": 1}})

    write_json(
        repo / "video_configs" / "pair_track_truth.json",
        {
            "pair_001": {"ali_source": "a0"},
            "pair_002": {"ali_source": "a1"},
        },
    )

    write_json(repo / "learning_corpus" / "pairs" / "pair_001" / "style_fingerprint.json", {"kind": "pair"})
    write_json(repo / "learning_corpus" / "top_solo" / "solo_001" / "style_fingerprint.json", {"kind": "solo"})
    write_json(repo / "learning_corpus" / "vlogs" / "vlog_001" / "style_fingerprint.json", {"kind": "vlog"})

    return repo


def test_script_can_be_imported():
    module = load_module()
    assert module.PHASE == "P5-L2"
    assert module.MODE == "analysis_only_dry_run"


def test_script_does_not_use_forbidden_imports_or_calls():
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    forbidden_patterns = [
        "import subprocess",
        "from subprocess",
        "import requests",
        "from requests",
        "import urllib",
        "from urllib",
        "ollama",
        "api/generate",
        "ffmpeg",
        "whisper",
        "render_short",
        "shutil.rmtree",
        ".unlink(",
        "os.remove",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in text


def test_build_report_reads_safe_inputs_and_sets_counts(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    report = module.build_report(repo)

    assert report["status"] == "ok"
    assert report["phase"] == "P5-L2"
    assert report["mode"] == "analysis_only_dry_run"

    assert report["counts"]["pair_fingerprints"] == 1
    assert report["counts"]["top_solo_fingerprints"] == 1
    assert report["counts"]["vlog_fingerprints"] == 1
    assert report["counts"]["pair_truth_entries"] == 2

    assert "video_configs/pair_track_truth.json" in report["inputs_read"]
    assert "learning_corpus/pairs/pair_001/style_fingerprint.json" in report["inputs_read"]
    assert "learning_corpus/top_solo/solo_001/style_fingerprint.json" in report["inputs_read"]
    assert "learning_corpus/vlogs/vlog_001/style_fingerprint.json" in report["inputs_read"]


def test_report_safety_flags_are_false(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    report = module.build_report(repo)

    assert report["qwen_used"] is False
    assert report["render_used"] is False
    assert report["ingest_used"] is False
    assert report["music_used"] is False
    assert report["autocut_used"] is False
    assert report["learning_loop_started"] is False
    assert report["phase_5_5_used"] is False
    assert report["deleted_files"] == []


def test_write_report_only_writes_expected_files_in_output_dir(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)
    output_dir = repo / "reports" / "p5_l2_analysis_only_dry_run"

    report = module.build_report(repo)
    json_path, md_path = module.write_report(report, output_dir, repo)

    assert json_path == output_dir / "p5_l2_analysis_report.json"
    assert md_path == output_dir / "p5_l2_analysis_summary.md"
    assert json_path.exists()
    assert md_path.exists()

    written = sorted(path.relative_to(output_dir).as_posix() for path in output_dir.rglob("*") if path.is_file())
    assert written == [
        "p5_l2_analysis_report.json",
        "p5_l2_analysis_summary.md",
    ]


def test_validate_output_dir_allows_exact_reports_target(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    rel_out = module.validate_output_dir(repo, Path("reports") / "p5_l2_analysis_only_dry_run")
    abs_out = module.validate_output_dir(repo, repo / "reports" / "p5_l2_analysis_only_dry_run")

    assert rel_out == repo.resolve() / "reports" / "p5_l2_analysis_only_dry_run"
    assert abs_out == repo.resolve() / "reports" / "p5_l2_analysis_only_dry_run"


def test_validate_output_dir_rejects_wrong_reports_target(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    with pytest.raises(ValueError):
        module.validate_output_dir(repo, Path("reports") / "other")


def test_validate_output_dir_rejects_non_report_or_outside_targets(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    blocked = [
        Path("video_configs"),
        Path("learning_corpus"),
        Path(".."),
        tmp_path / "outside" / "reports" / "p5_l2_analysis_only_dry_run",
    ]

    for output_dir in blocked:
        with pytest.raises(ValueError):
            module.validate_output_dir(repo, output_dir)


def test_missing_pair_track_truth_returns_error(tmp_path: Path):
    module = load_module()
    repo = tmp_path / "repo_without_pair_truth"

    write_json(repo / "video_configs" / "gaming_pairs_style_dna.json", {"style": {"cuts": 3}})
    write_json(repo / "video_configs" / "top_solo_style_dna.json", {"style": {"cuts": 2}})
    write_json(repo / "video_configs" / "vlog_style_dna.json", {"style": {"cuts": 1}})

    write_json(repo / "learning_corpus" / "pairs" / "pair_001" / "style_fingerprint.json", {"kind": "pair"})
    write_json(repo / "learning_corpus" / "top_solo" / "solo_001" / "style_fingerprint.json", {"kind": "solo"})
    write_json(repo / "learning_corpus" / "vlogs" / "vlog_001" / "style_fingerprint.json", {"kind": "vlog"})

    report = module.build_report(repo)

    assert report["status"] == "error"
    assert report["pair_truth_validation"]["exists"] is False
    assert "Missing pair_track_truth.json." in report["warnings"]



def test_ali_voice_reference_is_forbidden_as_ali_source(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    write_json(
        repo / "video_configs" / "pair_track_truth.json",
        {
            "pair_001": {"ali_source": "ali_voice_reference.wav"},
        },
    )

    report = module.build_report(repo)

    assert report["status"] == "error"
    assert report["pair_truth_validation"]["uses_forbidden_ali_reference"] is True
    assert report["forbidden_inputs_used"]
    assert any("ali_voice_reference.wav" in item for item in report["forbidden_inputs_used"])


def test_invalid_ali_source_is_error(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    write_json(
        repo / "video_configs" / "pair_track_truth.json",
        {
            "pair_001": {"ali_source": "friend_track"},
        },
    )

    report = module.build_report(repo)

    assert report["status"] == "error"
    assert report["pair_truth_validation"]["invalid_ali_sources"]

def test_utf8_bom_json_files_are_supported(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    pair_truth_path = repo / "video_configs" / "pair_track_truth.json"
    pair_truth_path.write_text(
        json.dumps({"pair_001": {"ali_source": "a0"}}, indent=2),
        encoding="utf-8-sig",
    )

    report = module.build_report(repo)

    assert report["status"] == "ok"
    assert report["counts"]["pair_truth_entries"] == 1
    assert report["pair_truth_validation"]["ali_sources"]["pair_001"] == "a0"

def test_nested_pair_truth_schema_is_supported(tmp_path: Path):
    module = load_module()
    repo = make_fake_repo(tmp_path)

    write_json(
        repo / "video_configs" / "pair_track_truth.json",
        {
            "schema_version": "p5_g2_5_pair_track_truth_v1",
            "head": "f870b3f",
            "summary": {"pairs": 2},
            "pairs": {
                "pair_001": {"ali_source": "a0"},
                "pair_002": {"ali_source": "a1"},
            },
        },
    )

    report = module.build_report(repo)

    assert report["status"] == "ok"
    assert report["counts"]["pair_truth_entries"] == 2
    assert report["pair_truth_validation"]["schema_shape"] == "metadata_with_pairs"
    assert report["pair_truth_validation"]["ali_sources"]["pair_001"] == "a0"
    assert report["pair_truth_validation"]["ali_sources"]["pair_002"] == "a1"
    assert report["pair_truth_validation"]["invalid_ali_sources"] == []
