from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


MAPPING_VERSION = "2"
MAPPING_METHOD = "final_scene_inventory"
MAPPING_NOTES = "audio_alignment_not_feasible_structural_encoding_mismatch"
ALIGNMENT_NOTES = "final_scene_inventory_method_no_raw_alignment"

CUT_SELECTION_FILENAME = "cut_selection_map.json"
STYLE_FINGERPRINT_FILENAME = "style_fingerprint.json"
META_FILENAME = "meta.json"


@dataclass(frozen=True)
class FinalKeptSegment:
    final_start_s: float
    final_end_s: float
    estimated_duration_s: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FinalSceneInventoryMap:
    pair_id: str
    raw_duration_seconds: float
    final_duration_seconds: float
    mapping_method: str
    mapping_notes: str
    kept_segments: list[dict[str, Any]]
    cut_ratio: float
    total_kept_seconds: float
    total_cut_seconds: float
    alignment_confidence: None
    alignment_notes: str
    mapping_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_cut_selection_map(
    pair_path: str | Path,
    *,
    raw_audio_path: str | Path | None = None,
    final_audio_path: str | Path | None = None,
    power_profile: str | None = None,
    ffmpeg_path: str | None = None,
    ffprobe_path: str | None = None,
) -> dict[str, Any]:
    """
    Build a final-scene inventory cut-selection map.

    P5-2 no longer performs raw-to-final audio alignment because the local corpus
    uses structurally different raw recordings and edited exports. This method
    documents the final edit structure from P5-1 style_fingerprint.json.
    """

    pair_dir = Path(pair_path)
    pair_id = pair_dir.name

    style_fingerprint_path = pair_dir / STYLE_FINGERPRINT_FILENAME
    meta_path = pair_dir / META_FILENAME

    style_fingerprint = read_json_file(style_fingerprint_path)
    meta = read_json_file(meta_path)

    raw_duration = read_required_number(meta, "raw_duration_seconds")
    final_duration = read_required_number(meta, "final_duration_seconds")

    boundaries = extract_scene_boundaries_seconds(style_fingerprint)
    kept_segments = build_final_kept_segments(
        boundaries_seconds=boundaries,
        final_duration_seconds=final_duration,
    )

    total_kept = round(float(final_duration), 3)
    total_cut = round(max(0.0, float(raw_duration) - float(final_duration)), 3)
    cut_ratio = round(total_cut / raw_duration, 6) if raw_duration > 0 else 0.0

    return FinalSceneInventoryMap(
        pair_id=pair_id,
        raw_duration_seconds=round(raw_duration, 3),
        final_duration_seconds=round(final_duration, 3),
        mapping_method=MAPPING_METHOD,
        mapping_notes=MAPPING_NOTES,
        kept_segments=kept_segments,
        cut_ratio=cut_ratio,
        total_kept_seconds=total_kept,
        total_cut_seconds=total_cut,
        alignment_confidence=None,
        alignment_notes=ALIGNMENT_NOTES,
        mapping_version=MAPPING_VERSION,
    ).to_dict()


def extract_scene_boundaries_seconds(style_fingerprint: dict[str, Any]) -> list[float]:
    """
    Read scene_changes.boundaries_seconds from style_fingerprint.json.

    Supports a few defensive aliases because P5-1 fingerprints may evolve.
    """

    scene_changes = style_fingerprint.get("scene_changes")
    if not isinstance(scene_changes, dict):
        raise ValueError("style_fingerprint.json missing scene_changes object")

    candidates = [
        scene_changes.get("boundaries_seconds"),
        scene_changes.get("boundary_seconds"),
        scene_changes.get("boundaries"),
    ]

    for candidate in candidates:
        if isinstance(candidate, list):
            values = []
            for item in candidate:
                try:
                    value = float(item)
                except (TypeError, ValueError):
                    continue
                if value >= 0:
                    values.append(value)

            values = sorted(set(round(value, 3) for value in values))
            if values:
                return values

    raise ValueError("style_fingerprint.json scene_changes has no usable boundaries_seconds")


def build_final_kept_segments(
    *,
    boundaries_seconds: list[float],
    final_duration_seconds: float,
) -> list[dict[str, Any]]:
    """
    Convert final scene boundaries into final timeline kept segments.
    """

    final_duration = max(0.0, float(final_duration_seconds))
    clean_boundaries = [0.0]

    for boundary in boundaries_seconds:
        value = max(0.0, min(final_duration, float(boundary)))
        if value not in clean_boundaries:
            clean_boundaries.append(value)

    if final_duration not in clean_boundaries:
        clean_boundaries.append(final_duration)

    clean_boundaries = sorted(set(round(value, 3) for value in clean_boundaries))

    segments: list[dict[str, Any]] = []

    for start, end in zip(clean_boundaries, clean_boundaries[1:]):
        if end <= start:
            continue

        segment = FinalKeptSegment(
            final_start_s=round(start, 3),
            final_end_s=round(end, 3),
            estimated_duration_s=round(end - start, 3),
        ).to_dict()
        segments.append(segment)

    if not segments:
        raise ValueError("no final kept segments could be built from scene boundaries")

    return segments


def read_json_file(path: str | Path) -> dict[str, Any]:
    json_path = Path(path)
    if not json_path.exists():
        raise FileNotFoundError(f"Missing required P5-2 input file: {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {json_path}")

    return data


def read_required_number(payload: dict[str, Any], key: str) -> float:
    if key not in payload:
        raise ValueError(f"meta.json missing required key: {key}")

    try:
        value = float(payload[key])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"meta.json key {key!r} must be numeric") from exc

    if value < 0:
        raise ValueError(f"meta.json key {key!r} must not be negative")

    return value


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
