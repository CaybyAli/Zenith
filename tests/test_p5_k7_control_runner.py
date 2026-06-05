from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import k7_control_runner as runner


def _make_source(tmp_path: Path, relative: str = "input/raw.mp4") -> Path:
    source = tmp_path / relative
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b"fake video bytes")
    return source


def _output_dir(tmp_path: Path, suffix: str = "case") -> Path:
    return tmp_path / "reports" / "phase5" / "k7_control_run" / suffix


def _run_dry(tmp_path: Path, source: Path | None = None, duration: float = 60.0) -> Path:
    source_path = source or _make_source(tmp_path)
    output = _output_dir(tmp_path)
    return runner.main(
        [
            "--source",
            str(source_path),
            "--output-dir",
            str(output),
            "--duration",
            str(duration),
            "--pair-id",
            "pair_001",
            "--dry-run",
        ]
    )


def _read_plan(plan_path: Path) -> dict:
    return json.loads(plan_path.read_text(encoding="utf-8"))


def test_dry_run_writes_plan_json(tmp_path: Path) -> None:
    plan_path = _run_dry(tmp_path)

    assert plan_path.name == "k7_control_plan.json"
    assert plan_path.exists()

    plan = _read_plan(plan_path)
    assert plan["status"] == "dry_run_ok"
    assert plan["duration"] == 60.0
    assert plan["pair_id"] == "pair_001"

    output_files = list(plan_path.parent.rglob("*"))
    assert not [path for path in output_files if path.suffix.lower() in {".mp4", ".mov", ".mkv"}]


@pytest.mark.parametrize("folder", ["reports", "exports", "shorts"])
def test_rejects_reports_exports_shorts_sources(tmp_path: Path, folder: str) -> None:
    source = _make_source(tmp_path, f"{folder}/raw.mp4")

    with pytest.raises(RuntimeError, match="K7_SOURCE_FORBIDDEN_LOCATION"):
        _run_dry(tmp_path, source=source)


@pytest.mark.parametrize("token", ["caption", "subtitle", "preview", "proof", "emoji"])
def test_rejects_captioned_or_preview_source_names(tmp_path: Path, token: str) -> None:
    source = _make_source(tmp_path, f"input/{token}_raw.mp4")

    with pytest.raises(RuntimeError, match="K7_SOURCE_FORBIDDEN_NAME_TOKEN"):
        _run_dry(tmp_path, source=source)


def test_duration_guard(tmp_path: Path) -> None:
    source = _make_source(tmp_path)

    with pytest.raises(RuntimeError, match="K7_DURATION_OUT_OF_RANGE"):
        _run_dry(tmp_path, source=source, duration=9.99)

    with pytest.raises(RuntimeError, match="K7_DURATION_OUT_OF_RANGE"):
        _run_dry(tmp_path, source=source, duration=120.1)

    plan_path = _run_dry(tmp_path, source=source, duration=60)
    assert _read_plan(plan_path)["duration"] == 60.0


def test_real_run_disabled(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    output = _output_dir(tmp_path)

    with pytest.raises(RuntimeError, match="K7_REAL_RUN_NOT_ENABLED_YET"):
        runner.main(
            [
                "--source",
                str(source),
                "--output-dir",
                str(output),
                "--duration",
                "60",
                "--pair-id",
                "pair_001",
            ]
        )


def test_pair_truth_ali_source_used(tmp_path: Path) -> None:
    plan_path = _run_dry(tmp_path)
    plan = _read_plan(plan_path)

    assert plan["ali_source"] == "a0"
    assert plan["pair_truth_source"] == "video_configs/pair_track_truth.json"
    assert plan["legacy_trackmap_trusted"] is False

    source_text = Path(runner.__file__).read_text(encoding="utf-8")
    assert "speaker_distribution" not in source_text
    assert "track_mapping" not in source_text


def test_plan_disables_qwen_music_ingest_phase55(tmp_path: Path) -> None:
    plan = _read_plan(_run_dry(tmp_path))

    assert plan["qwen"] is False
    assert plan["music"] is False
    assert plan["ingest"] is False
    assert plan["phase5_5"] is False
    assert plan["full_batch"] is False


def test_output_dir_guard(tmp_path: Path) -> None:
    source = _make_source(tmp_path)
    bad_output = tmp_path / "not_allowed"

    with pytest.raises(RuntimeError, match="K7_OUTPUT_DIR_MUST_BE_UNDER_REPORTS_PHASE5_K7_CONTROL_RUN"):
        runner.main(
            [
                "--source",
                str(source),
                "--output-dir",
                str(bad_output),
                "--duration",
                "60",
                "--pair-id",
                "pair_001",
                "--dry-run",
            ]
        )
