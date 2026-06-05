import ast
import json
from pathlib import Path

import pytest

from scripts import p5_l3_style_memory_safe_write as safe_write


SAFE_FALSE_KEYS = [
    "qwen_used",
    "render_used",
    "ingest_used",
    "music_used",
    "autocut_used",
    "overnight_started",
    "learning_loop_started",
    "phase_5_5_used",
    "production_files_modified",
    "video_configs_modified",
    "learning_corpus_modified",
    "obsidian_modified_by_script",
    "core_modified",
]


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _style_payload(prefix: str, count: int, forbidden: bool = False):
    items = []
    for index in range(1, count + 1):
        source = f"learning_corpus/{prefix}/item_{index:03d}"
        if forbidden and index == 1:
            source = "ali_voice_reference.wav"
        items.append({"source": source, "style": {"pace": "safe"}})

    return {
        "schema_version": "test_style_dna_v1",
        "items": items,
    }


def _make_fake_repo(tmp_path: Path, with_p5_l2: bool = True, forbidden: bool = False):
    repo = tmp_path / "repo"
    repo.mkdir()

    if with_p5_l2:
        _write_json(
            repo / "reports" / "p5_l2_analysis_only_dry_run" / "p5_l2_analysis_report.json",
            {
                "status": "ok",
                "source_counts": {
                    "pair_fingerprints": 20,
                    "top_solo_fingerprints": 30,
                    "vlog_fingerprints": 3,
                    "pair_truth_entries": 20,
                },
                "qwen_used": False,
                "render_used": False,
                "ingest_used": False,
                "music_used": False,
            },
        )

    _write_json(
        repo / "video_configs" / "gaming_pairs_style_dna.json",
        _style_payload("pairs", 20, forbidden=forbidden),
    )
    _write_json(
        repo / "video_configs" / "top_solo_style_dna.json",
        _style_payload("top_solo", 30),
    )
    _write_json(
        repo / "video_configs" / "vlog_style_dna.json",
        _style_payload("vlogs", 3),
    )
    _write_json(
        repo / "video_configs" / "pair_track_truth.json",
        {
            "pairs": {
                f"pair_{index:03d}": {"ali_source": "a0", "friend_source": "a1"}
                for index in range(1, 21)
            }
        },
    )

    for protected_dir in ("core", "learning_corpus", "obsidian_zenith"):
        (repo / protected_dir).mkdir(parents=True, exist_ok=True)

    return repo


def _files_under(path: Path):
    if not path.exists():
        return set()
    return {
        item.relative_to(path).as_posix()
        for item in path.rglob("*")
        if item.is_file()
    }


def test_script_importable():
    assert hasattr(safe_write, "build_style_memory_safe_write")


def test_forbidden_imports_and_real_usage_are_absent():
    script_path = Path(safe_write.__file__)
    text = script_path.read_text(encoding="utf-8-sig")
    tree = ast.parse(text)

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])

    for forbidden_import in ("sub" + "process", "req" + "uests", "url" + "lib", "ol" + "lama"):
        assert forbidden_import not in imports

    assert ("ff" + "mpeg") not in text.lower()
    assert ("whis" + "per") not in text.lower()
    assert ("render" + "_short(") not in text
    assert ("shutil" + "." + "rm" + "tree") not in text
    assert ("os" + "." + "remove") not in text
    assert ("." + "un" + "link(") not in text


def test_fake_repo_writes_expected_outputs(tmp_path):
    repo = _make_fake_repo(tmp_path)
    output_dir = repo / "reports" / "p5_l3_style_memory_safe_write"

    manifest = safe_write.build_style_memory_safe_write(repo, output_dir)

    assert manifest["status"] == "ok"
    assert manifest["phase"] == "P5-L3"
    assert manifest["mode"] == "style_memory_safe_write"
    assert manifest["memory_write_target"] == "reports_only_candidate"
    assert manifest["writes_only_under"] == "reports/p5_l3_style_memory_safe_write"

    candidate_path = output_dir / "style_memory_candidate.json"
    manifest_path = output_dir / "style_memory_manifest.json"
    summary_path = output_dir / "style_memory_summary.md"

    assert candidate_path.exists()
    assert manifest_path.exists()
    assert summary_path.exists()

    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert candidate["status"] == "candidate_only"
    assert candidate["memory_version"] == "p5_l3_candidate_v1"
    assert candidate["can_be_used_for_production"] is False
    assert candidate["owner_review_required"] is True
    assert set(candidate["style_categories"].keys()) == {
        "gaming_pairs",
        "top_solo",
        "vlog",
    }

    assert manifest["source_counts"] == {
        "pair_fingerprints": 20,
        "top_solo_fingerprints": 30,
        "vlog_fingerprints": 3,
        "pair_truth_entries": 20,
    }


def test_safety_flags_are_false(tmp_path):
    repo = _make_fake_repo(tmp_path)
    output_dir = repo / "reports" / "p5_l3_style_memory_safe_write"

    manifest = safe_write.build_style_memory_safe_write(repo, output_dir)

    for key in SAFE_FALSE_KEYS:
        assert manifest[key] is False

    assert manifest["deleted_files"] == []


def test_output_scope_only_reports_p5_l3(tmp_path):
    repo = _make_fake_repo(tmp_path)
    output_dir = repo / "reports" / "p5_l3_style_memory_safe_write"

    protected_before = {
        "video_configs": _files_under(repo / "video_configs"),
        "learning_corpus": _files_under(repo / "learning_corpus"),
        "obsidian_zenith": _files_under(repo / "obsidian_zenith"),
        "core": _files_under(repo / "core"),
    }

    manifest = safe_write.build_style_memory_safe_write(repo, output_dir)

    protected_after = {
        "video_configs": _files_under(repo / "video_configs"),
        "learning_corpus": _files_under(repo / "learning_corpus"),
        "obsidian_zenith": _files_under(repo / "obsidian_zenith"),
        "core": _files_under(repo / "core"),
    }

    assert protected_after == protected_before

    assert set(_files_under(output_dir)) == {
        "style_memory_candidate.json",
        "style_memory_manifest.json",
        "style_memory_summary.md",
    }

    for output in manifest["outputs_written"]:
        assert output.startswith("reports/p5_l3_style_memory_safe_write/")


def test_missing_p5_l2_report_errors(tmp_path):
    repo = _make_fake_repo(tmp_path, with_p5_l2=False)
    output_dir = repo / "reports" / "p5_l3_style_memory_safe_write"

    with pytest.raises(FileNotFoundError):
        safe_write.build_style_memory_safe_write(repo, output_dir)


def test_output_outside_allowed_folder_errors(tmp_path):
    repo = _make_fake_repo(tmp_path)

    with pytest.raises(ValueError):
        safe_write.build_style_memory_safe_write(repo, repo / "reports" / "wrong_folder")


def test_ali_voice_reference_is_forbidden(tmp_path):
    repo = _make_fake_repo(tmp_path, forbidden=True)
    output_dir = repo / "reports" / "p5_l3_style_memory_safe_write"

    manifest = safe_write.build_style_memory_safe_write(repo, output_dir)

    assert manifest["status"] == "error"
    assert manifest["forbidden_inputs_used"]
    assert "ali_voice_reference.wav" in manifest["forbidden_inputs_used"][0]
