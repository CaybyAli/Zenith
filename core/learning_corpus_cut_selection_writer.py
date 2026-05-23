from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CUT_SELECTION_FILENAME = "cut_selection_map.json"
CUT_SELECTION_MAPPING_VERSION = "1"
DEFAULT_DURATION_TOLERANCE_SECONDS = 1.0
DEFAULT_MIN_ALIGNMENT_CONFIDENCE = 0.85
_ALLOWED_CUT_REASONS = {"low_action", "dead_air", "unknown"}


class CutSelectionValidationError(ValueError):
    """Raised when cut_selection_map.json would be invalid."""


@dataclass(frozen=True)
class CutSelectionValidationResult:
    pair_id: str
    kept_seconds: float
    final_duration_seconds: float
    kept_final_diff_seconds: float
    alignment_confidence: float
    valid: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_id": self.pair_id,
            "kept_seconds": self.kept_seconds,
            "final_duration_seconds": self.final_duration_seconds,
            "kept_final_diff_seconds": self.kept_final_diff_seconds,
            "alignment_confidence": self.alignment_confidence,
            "valid": self.valid,
        }


def write_cut_selection_map(
    pair_path: str | Path,
    cut_selection_map: dict[str, Any],
    *,
    duration_tolerance_seconds: float = DEFAULT_DURATION_TOLERANCE_SECONDS,
    min_alignment_confidence: float = DEFAULT_MIN_ALIGNMENT_CONFIDENCE,
    report_dir: str | Path = Path("reports/phase5/p5-2"),
) -> Path:
    """
    Validate and write cut_selection_map.json beside raw.mp4 in pair_NNN.

    On validation failure, a STOPP report is written and the JSON is not saved.
    """

    pair_dir = Path(pair_path)
    pair_dir.mkdir(parents=True, exist_ok=True)

    normalized = normalize_cut_selection_map(cut_selection_map, pair_id_fallback=pair_dir.name)

    try:
        validate_cut_selection_map(
            normalized,
            duration_tolerance_seconds=duration_tolerance_seconds,
            min_alignment_confidence=min_alignment_confidence,
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
    duration_tolerance_seconds: float = DEFAULT_DURATION_TOLERANCE_SECONDS,
    min_alignment_confidence: float = DEFAULT_MIN_ALIGNMENT_CONFIDENCE,
) -> CutSelectionValidationResult:
    """Validate the P5-2 cut-selection schema and duration/confidence rules."""

    required = {
        "pair_id",
        "raw_duration_seconds",
        "final_duration_seconds",
        "kept_segments",
        "cut_segments",
        "alignment_confidence",
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

    raw_duration = _safe_float(cut_selection_map.get("raw_duration_seconds"), default=-1.0)
    final_duration = _safe_float(cut_selection_map.get("final_duration_seconds"), default=-1.0)
    if raw_duration <= 0:
        raise CutSelectionValidationError("raw_duration_seconds must be greater than zero")
    if final_duration <= 0:
        raise CutSelectionValidationError("final_duration_seconds must be greater than zero")

    kept_segments = cut_selection_map.get("kept_segments")
    cut_segments = cut_selection_map.get("cut_segments")
    if not isinstance(kept_segments, list):
        raise CutSelectionValidationError("kept_segments must be a list")
    if not isinstance(cut_segments, list):
        raise CutSelectionValidationError("cut_segments must be a list")
    if not kept_segments:
        raise CutSelectionValidationError("kept_segments must not be empty")

    kept_seconds = 0.0
    previous_end = 0.0
    for index, segment in enumerate(kept_segments):
        if not isinstance(segment, dict):
            raise CutSelectionValidationError(f"kept_segments[{index}] must be an object")

        raw_start = _safe_float(segment.get("raw_start_s"), default=-1.0)
        raw_end = _safe_float(segment.get("raw_end_s"), default=-1.0)
        final_start = _safe_float(segment.get("final_start_s"), default=-1.0)

        if raw_start < 0 or raw_end <= raw_start:
            raise CutSelectionValidationError(
                f"kept_segments[{index}] has invalid raw range {raw_start}..{raw_end}"
            )
        if raw_end > raw_duration + 0.001:
            raise CutSelectionValidationError(
                f"kept_segments[{index}] exceeds raw duration: {raw_end} > {raw_duration}"
            )
        if final_start < 0:
            raise CutSelectionValidationError(f"kept_segments[{index}].final_start_s is invalid")
        if raw_start < previous_end - 0.001:
            raise CutSelectionValidationError("kept_segments must be sorted and non-overlapping")

        kept_seconds += raw_end - raw_start
        previous_end = raw_end

    for index, segment in enumerate(cut_segments):
        if not isinstance(segment, dict):
            raise CutSelectionValidationError(f"cut_segments[{index}] must be an object")

        raw_start = _safe_float(segment.get("raw_start_s"), default=-1.0)
        raw_end = _safe_float(segment.get("raw_end_s"), default=-1.0)
        reason = str(segment.get("cut_reason_class") or "unknown")

        if raw_start < 0 or raw_end <= raw_start:
            raise CutSelectionValidationError(
                f"cut_segments[{index}] has invalid raw range {raw_start}..{raw_end}"
            )
        if raw_end > raw_duration + 0.001:
            raise CutSelectionValidationError(
                f"cut_segments[{index}] exceeds raw duration: {raw_end} > {raw_duration}"
            )
        if reason not in _ALLOWED_CUT_REASONS:
            raise CutSelectionValidationError(
                f"cut_segments[{index}].cut_reason_class is invalid: {reason!r}"
            )

    alignment_confidence = _safe_float(cut_selection_map.get("alignment_confidence"), default=-1.0)
    if alignment_confidence < min_alignment_confidence:
        raise CutSelectionValidationError(
            f"alignment_confidence below threshold: {alignment_confidence:.6f} < {min_alignment_confidence:.6f}"
        )

    diff = abs(kept_seconds - final_duration)
    result = CutSelectionValidationResult(
        pair_id=pair_id,
        kept_seconds=round(kept_seconds, 3),
        final_duration_seconds=round(final_duration, 3),
        kept_final_diff_seconds=round(diff, 3),
        alignment_confidence=round(alignment_confidence, 6),
        valid=diff <= duration_tolerance_seconds,
    )

    if not result.valid:
        raise CutSelectionValidationError(
            "kept seconds outside tolerance: "
            f"kept={result.kept_seconds:.3f}, "
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
    """Normalize a cut-selection map into stable JSON-safe values."""

    payload = cut_selection_map or {}
    pair_id = str(payload.get("pair_id") or pair_id_fallback).strip()

    kept_segments = []
    for segment in payload.get("kept_segments", []) or []:
        if not isinstance(segment, dict):
            continue
        kept_segments.append(
            {
                "raw_start_s": _round_seconds(segment.get("raw_start_s", 0.0)),
                "raw_end_s": _round_seconds(segment.get("raw_end_s", 0.0)),
                "final_start_s": _round_seconds(segment.get("final_start_s", 0.0)),
            }
        )

    cut_segments = []
    for segment in payload.get("cut_segments", []) or []:
        if not isinstance(segment, dict):
            continue
        reason = str(segment.get("cut_reason_class") or "unknown")
        if reason not in _ALLOWED_CUT_REASONS:
            reason = "unknown"
        cut_segments.append(
            {
                "raw_start_s": _round_seconds(segment.get("raw_start_s", 0.0)),
                "raw_end_s": _round_seconds(segment.get("raw_end_s", 0.0)),
                "cut_reason_class": reason,
            }
        )

    return {
        "pair_id": pair_id,
        "raw_duration_seconds": _round_seconds(payload.get("raw_duration_seconds", 0.0)),
        "final_duration_seconds": _round_seconds(payload.get("final_duration_seconds", 0.0)),
        "kept_segments": kept_segments,
        "cut_segments": cut_segments,
        "alignment_confidence": round(
            _safe_float(payload.get("alignment_confidence"), default=0.0),
            6,
        ),
        "mapping_version": str(payload.get("mapping_version") or CUT_SELECTION_MAPPING_VERSION),
    }


def serialize_cut_selection_map(cut_selection_map: dict[str, Any]) -> str:
    """Serialize deterministically with stable key order and trailing newline."""

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
    """Write a STOPP report for invalid pair alignment/validation."""

    report_root = Path(report_dir)
    report_root.mkdir(parents=True, exist_ok=True)

    pair_id = str(cut_selection_map.get("pair_id") or "unknown_pair")
    kept_seconds = sum_kept_seconds(cut_selection_map)
    final_duration = _safe_float(cut_selection_map.get("final_duration_seconds"), default=0.0)
    confidence = _safe_float(cut_selection_map.get("alignment_confidence"), default=0.0)

    report_path = report_root / f"STOPP_CUT_SELECTION_{pair_id}.md"
    report = "\n".join(
        [
            f"# P5-2 STOPP-Bericht {pair_id}",
            "",
            "Status: blockiert",
            "",
            f"Grund: {reason}",
            "",
            "Messwerte:",
            f"- pair_id: {pair_id}",
            f"- alignment_confidence: {confidence:.6f}",
            f"- kept_seconds_sum: {kept_seconds:.3f}",
            f"- final_duration_seconds: {final_duration:.3f}",
            f"- diff_seconds: {abs(kept_seconds - final_duration):.3f}",
            "",
            "Vorschlag:",
            "- Pair manuell prüfen.",
            "- Audio-Alignment-Fenster/Segmentierung prüfen.",
            "- cut_selection_map.json für dieses Pair nicht akzeptieren, bis Confidence und Dauer-Validierung grün sind.",
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
        start = _safe_float(segment.get("raw_start_s"), default=0.0)
        end = _safe_float(segment.get("raw_end_s"), default=start)
        total += max(0.0, end - start)
    return round(total, 3)


def _safe_float(value: Any, *, default: float) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return default
    return converted


def _round_seconds(value: Any) -> float:
    return round(_safe_float(value, default=0.0), 3)
