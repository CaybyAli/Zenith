from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import pair_track_truth_loader

PLAN_FILENAME = "k7_control_plan.json"
MIN_DURATION_SECONDS = 10.0
MAX_DURATION_SECONDS = 120.0
BLOCKED_SOURCE_PARTS = {"reports", "exports", "shorts"}
BLOCKED_SOURCE_NAME_TOKENS = ("caption", "subtitle", "preview", "proof", "emoji")
ALLOWED_SOURCE_EXTENSIONS = {".mp4", ".mov", ".mkv"}
OUTPUT_DIR_SEQUENCE = ("reports", "phase5", "k7_control_run")


def _casefold_parts(path: Path) -> list[str]:
    return [part.casefold() for part in path.parts]


def _path_contains_part(path: Path, blocked_parts: set[str]) -> bool:
    parts = set(_casefold_parts(path))
    return bool(parts.intersection(blocked_parts))


def _path_contains_sequence(path: Path, sequence: tuple[str, ...]) -> bool:
    parts = _casefold_parts(path.resolve())
    wanted = [item.casefold() for item in sequence]
    width = len(wanted)

    for index in range(0, max(0, len(parts) - width + 1)):
        if parts[index:index + width] == wanted:
            return True

    return False


def validate_source_path(source: str | Path) -> Path:
    path = Path(source)

    if not path.exists():
        raise RuntimeError("K7_SOURCE_NOT_FOUND")

    if not path.is_file():
        raise RuntimeError("K7_SOURCE_NOT_FILE")

    if path.suffix.casefold() not in ALLOWED_SOURCE_EXTENSIONS:
        raise RuntimeError("K7_SOURCE_EXTENSION_NOT_ALLOWED")

    if _path_contains_part(path, BLOCKED_SOURCE_PARTS):
        raise RuntimeError("K7_SOURCE_FORBIDDEN_LOCATION")

    name = path.name.casefold()
    if any(token in name for token in BLOCKED_SOURCE_NAME_TOKENS):
        raise RuntimeError("K7_SOURCE_FORBIDDEN_NAME_TOKEN")

    return path.resolve()


def validate_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)

    if not _path_contains_sequence(path, OUTPUT_DIR_SEQUENCE):
        raise RuntimeError("K7_OUTPUT_DIR_MUST_BE_UNDER_REPORTS_PHASE5_K7_CONTROL_RUN")

    return path.resolve()


def validate_duration(duration: float) -> float:
    value = float(duration)

    if value < MIN_DURATION_SECONDS or value > MAX_DURATION_SECONDS:
        raise RuntimeError("K7_DURATION_OUT_OF_RANGE")

    return value


def load_pair_truth_entry(pair_id: str) -> dict[str, Any]:
    truth = pair_track_truth_loader.load_truth()

    if pair_id not in truth:
        raise RuntimeError("K7_PAIR_ID_NOT_FOUND_IN_PAIR_TRACK_TRUTH")

    entry = truth[pair_id]
    if not isinstance(entry, dict):
        raise RuntimeError("K7_PAIR_TRUTH_ENTRY_INVALID")

    return entry


def build_plan(
    *,
    source: Path,
    output_dir: Path,
    duration: float,
    pair_id: str,
) -> dict[str, Any]:
    ali_source = pair_track_truth_loader.get_ali_source(pair_id)
    truth_entry = load_pair_truth_entry(pair_id)

    if not ali_source:
        raise RuntimeError("K7_ALI_SOURCE_MISSING")

    return {
        "status": "dry_run_ok",
        "source": str(source),
        "output_dir": str(output_dir),
        "duration": float(duration),
        "pair_id": pair_id,
        "ali_source": ali_source,
        "friend_source": truth_entry.get("friend_source"),
        "game_source": truth_entry.get("game_source"),
        "qwen": False,
        "music": False,
        "ingest": False,
        "phase5_5": False,
        "full_batch": False,
        "clean_source_guard": True,
        "pair_truth_source": "video_configs/pair_track_truth.json",
        "legacy_trackmap_trusted": False,
        "expected_next_step": "real_control_run_after_master_go",
    }


def write_plan(plan: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_path = output_dir / PLAN_FILENAME
    plan_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return plan_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="K7 control-run guard runner. Dry-run only in foundation stage."
    )
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--pair-id", default="pair_001")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-qwen", action="store_true", default=True)
    parser.add_argument("--no-music", action="store_true", default=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> Path:
    args = parse_args(argv)

    source = validate_source_path(args.source)
    output_dir = validate_output_dir(args.output_dir)
    duration = validate_duration(args.duration)

    plan = build_plan(
        source=source,
        output_dir=output_dir,
        duration=duration,
        pair_id=str(args.pair_id),
    )

    if not args.dry_run:
        raise RuntimeError("K7_REAL_RUN_NOT_ENABLED_YET")

    plan_path = write_plan(plan, output_dir)
    print(f"K7_CONTROL_DRY_RUN_OK={plan_path}")
    return plan_path


if __name__ == "__main__":
    main()
