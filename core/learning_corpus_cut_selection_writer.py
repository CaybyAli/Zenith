from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CUT_SELECTION_FILENAME = "cut_selection_map.json"
CUT_SELECTION_MAPPING_VERSION = "2"
DEFAULT_FINAL_DURATION_TOLERANCE_SECONDS = 5.0
EXPECTED_MAPPING_METHOD = "final_scene_inventory"
EXPECTED_ALIGNMENT_NOTES = "final_scene_inventory_method_no_raw_alignment"


class CutSelectionValidationError(ValueError):
    """Raised when cut_selection_map.json would be invalid."""


@dataclass(frozen=True)
class CutSelectionValidationResult:
    pair_id: str
    total_kept_seconds: float
    final_duration_seconds: float
    kept_final_diff_seconds: float
    cut_ratio: float
    valid: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "total_kept_seconds": self.total_kept_seconds,
            "final_duration_seconds": self.final_duration_seconds,
            "kept_final_diff_seconds": self.kept_final_diff_seconds,
            "cut_ratio": self.cut_ratio,
            "valid": self.valid,
        }


def write_cut_selection_map(
    pair_path: str | Path,
    cut_selection_map: dict[str, Any],
    *,
    duration_tolerance_seconds: float = DEFAULT_FINAL_DURATION_TOLERANCE_SECONDS,
    report_dir: str | Path = Path("reports/phase5/p5-2"),
    **_: Any,
) -> Path:
    """
    Validate and write mapping_version=2 final-scene inventory cut_selection_map.json.
    """

    pair_dir = Path(pair_path)
    pair_dir.mkdir(parents=True, exist_ok=True)

    normalized = normalize_cut_selection_map(cut_selection_map, pair_id_fallback=pair_dir.name)

    try:
        validate_cut_selection_map(
            normalized,
            duration_tolerance_seconds=duration_tolerance_seconds,
        )
    except CutSelectionValidationError as exc:
        write_cut_selection_stopp_report(
            normalized,
            reason=str(exc),
            report_dir=report_dir,
        )
        raise

    output_path = pair_dir / CUT_SELECTION_FILENAME
    temp_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")

    serialized = serialize_cut_selection_map(normalized)

    try:
        temp_path.write_text(serialized, encoding="utf-8", newline="\n")
        temp_path.replace(output_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return output_path


def validate_cut_selection_map(
    cut_selection_map: dict[str, Any],
    *,
    duration_tolerance_seconds: float = DEFAULT_FINAL_DURATION_TOLERANCE_SECONDS,
    **_: Any,
) -> CutSelectionValidationResult:
    required = {
        "pair_id",
        "raw_duration_seconds",
        "final_duration_seconds",
        "mapping_method",
        "mapping_notes",
        "kept_segments",
        "cut_ratio",
        "total_kept_seconds",
        "total_cut_seconds",
        "alignment_confidence",
        "alignment_notes",
        "mapping_version",
    }

    missing = sorted(required - set(cut_selection_map))
    if missing:
        raise CutSelectionValidationError(f"missing required keys: {missing}")

    pair_id = str(cut_selection_map.get("pair_id") or "").strip()
    if not pair_id:
        raise CutSelectionValidationError("pair_id is required")

    mapping_version = str(cut_selection_map.get("mapping_version") or "")
    if mapping_version != CUT_SELECTION_MAPPING_VERSION:
        raise CutSelectionValidationError(
            f"mapping_version must be {CUT_SELECTION_MAPPING_VERSION!r}, got {mapping_version!r}"
        )

    mapping_method = str(cut_selection_map.get("mapping_method") or "")
    if mapping_method != EXPECTED_MAPPING_METHOD:
        raise CutSelectionValidationError(
            f"mapping_method must be {EXPECTED_MAPPING_METHOD!r}, got {mapping_method!r}"
        )

    alignment_notes = str(cut_selection_map.get("alignment_notes") or "")
    if alignment_notes != EXPECTED_ALIGNMENT_NOTES:
        raise CutSelectionValidationError(
            f"alignment_notes must be {EXPECTED_ALIGNMENT_NOTES!r}, got {alignment_notes!r}"
        )

    if cut_selection_map.get("alignment_confidence") is not None:
        raise CutSelectionValidationError("alignment_confidence must be null for final_scene_inventory")

    raw_duration = _safe_float(cut_selection_map.get("raw_duration_seconds"), default=-1.0)
    final_duration = _safe_float(cut_selection_map.get("final_duration_seconds"), default=-1.0)
    total_kept = _safe_float(cut_selection_map.get("total_kept_seconds"), default=-1.0)
    total_cut = _safe_float(cut_selection_map.get("total_cut_seconds"), default=-1.0)
    cut_ratio = _safe_float(cut_selection_map.get("cut_ratio"), default=-1.0)

    if raw_duration <= 0:
        raise CutSelectionValidationError("raw_duration_seconds must be greater than zero")
    if final_duration <= 0:
        raise CutSelectionValidationError("final_duration_seconds must be greater than zero")
    if total_kept <= 0:
        raise CutSelectionValidationError("total_kept_seconds must be greater than zero")
    if total_cut < 0:
        raise CutSelectionValidationError("total_cut_seconds must not be negative")
    if cut_ratio < 0.0 or cut_ratio > 1.0:
        raise CutSelectionValidationError("cut_ratio must be between 0.0 and 1.0")

    kept_segments = cut_selection_map.get("kept_segments")
    if not isinstance(kept_segments, list):
        raise CutSelectionValidationError("kept_segments must be a list")
    if not kept_segments:
        raise CutSelectionValidationError("kept_segments must not be empty")

    estimated_sum = 0.0
    previous_end = 0.0

    for index, segment in enumerate(kept_segments):
        if not isinstance(segment, dict):
            raise CutSelectionValidationError(f"kept_segments[{index}] must be an object")

        final_start = _safe_float(segment.get("final_start_s"), default=-1.0)
        final_end = _safe_float(segment.get("final_end_s"), default=-1.0)
        estimated_duration = _safe_float(segment.get("estimated_duration_s"), default=-1.0)

        if final_start < 0 or final_end <= final_start:
            raise CutSelectionValidationError(
                f"kept_segments[{index}] has invalid final range {final_start}..{final_end}"
            )
        if final_end > final_duration + duration_tolerance_seconds:
            raise CutSelectionValidationError(
                f"kept_segments[{index}] exceeds final duration: {final_end} > {final_duration}"
            )
        if final_start < previous_end - 0.001:
            raise CutSelectionValidationError("kept_segments must be sorted and non-overlapping")
        if estimated_duration <= 0:
            raise CutSelectionValidationError(f"kept_segments[{index}].estimated_duration_s is invalid")

        estimated_sum += estimated_duration
        previous_end = final_end

    diff = abs(estimated_sum - final_duration)

    result = CutSelectionValidationResult(
        pair_id=pair_id,
        total_kept_seconds=round(estimated_sum, 3),
        final_duration_seconds=round(final_duration, 3),
        kept_final_diff_seconds=round(diff, 3),
        cut_ratio=round(cut_ratio, 6),
        valid=diff <= duration_tolerance_seconds,
    )

    if not result.valid:
        raise CutSelectionValidationError(
            "estimated kept seconds outside tolerance: "
            f"kept={result.total_kept_seconds:.3f}, "
            f"final={result.final_duration_seconds:.3f}, "
            f"diff={result.kept_final_diff_seconds:.3f}, "
            f"tolerance={duration_tolerance_seconds:.3f}"
        )

    return result


def normalize_cut_selection_map(
    cut_selection_map: dict[str, Any],
    *,
    pair_id_fallback: str,
) -> dict[str, Any]:
    payload = cut_selection_map or {}

    kept_segments = []
    for segment in payload.get("kept_segments", []) or []:
        if not isinstance(segment, dict):
            continue

        kept_segments.append(
            {
                "final_start_s": _round_seconds(segment.get("final_start_s", 0.0)),
                "final_end_s": _round_seconds(segment.get("final_end_s", 0.0)),
                "estimated_duration_s": _round_seconds(segment.get("estimated_duration_s", 0.0)),
            }
        )

    return {
        "pair_id": str(payload.get("pair_id") or pair_id_fallback).strip(),
        "raw_duration_seconds": _round_seconds(payload.get("raw_duration_seconds", 0.0)),
        "final_duration_seconds": _round_seconds(payload.get("final_duration_seconds", 0.0)),
        "mapping_method": str(payload.get("mapping_method") or EXPECTED_MAPPING_METHOD),
        "mapping_notes": str(
            payload.get("mapping_notes")
            or "audio_alignment_not_feasible_structural_encoding_mismatch"
        ),
        "kept_segments": kept_segments,
        "cut_ratio": round(_safe_float(payload.get("cut_ratio"), default=0.0), 6),
        "total_kept_seconds": _round_seconds(payload.get("total_kept_seconds", 0.0)),
        "total_cut_seconds": _round_seconds(payload.get("total_cut_seconds", 0.0)),
        "alignment_confidence": None,
        "alignment_notes": str(payload.get("alignment_notes") or EXPECTED_ALIGNMENT_NOTES),
        "mapping_version": str(payload.get("mapping_version") or CUT_SELECTION_MAPPING_VERSION),
    }


def serialize_cut_selection_map(cut_selection_map: dict[str, Any]) -> str:
    return (
        json.dumps(
            cut_selection_map,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    )


def write_cut_selection_stopp_report(
    cut_selection_map: dict[str, Any],
    *,
    reason: str,
    report_dir: str | Path,
) -> Path:
    report_root = Path(report_dir)
    report_root.mkdir(parents=True, exist_ok=True)

    pair_id = str(cut_selection_map.get("pair_id") or "unknown_pair")
    report_path = report_root / f"STOPP_CUT_SELECTION_{pair_id}.md"

    report = "\n".join(
        [
            f"# P5-2 STOPP-Bericht {pair_id}",
            "",
            "Status: blockiert",
            "",
            f"Grund: {reason}",
            "",
            "Methode:",
            "- mapping_method: final_scene_inventory",
            "- raw-to-final audio alignment wurde bewusst aufgegeben.",
            "",
        ]
    )

    report_path.write_text(report, encoding="utf-8", newline="\n")
    return report_path


def sum_kept_seconds(cut_selection_map: dict[str, Any]) -> float:
    total = 0.0
    for segment in cut_selection_map.get("kept_segments", []) or []:
        if not isinstance(segment, dict):
            continue
        total += max(0.0, _safe_float(segment.get("estimated_duration_s"), default=0.0))
    return round(total, 3)


def _safe_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _round_seconds(value: Any) -> float:
    return round(_safe_float(value, default=0.0), 3)
