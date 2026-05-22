from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PacingMetricsResult:
    """Stable pacing payload used by style_fingerprint.json."""

    cut_count: int
    cuts_per_minute: float
    median_clip_seconds: float
    clip_length_histogram_bins: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_DEFAULT_HISTOGRAM_BINS: tuple[tuple[str, float, float | None], ...] = (
    ("0-2s", 0.0, 2.0),
    ("2-5s", 2.0, 5.0),
    ("5-10s", 5.0, 10.0),
    ("10-20s", 10.0, 20.0),
    ("20s+", 20.0, None),
)


def extract_pacing_metrics(
    boundaries_seconds: list[float] | tuple[float, ...],
    *,
    duration_seconds: float,
) -> dict[str, Any]:
    """
    Derive pacing metrics from scene-change boundaries.

    Output schema:
    - cut_count
    - cuts_per_minute
    - median_clip_seconds
    - clip_length_histogram_bins
    """

    clean_duration = _safe_non_negative_float(duration_seconds)
    clean_boundaries = normalize_boundaries(boundaries_seconds, duration_seconds=clean_duration)

    clip_lengths = build_clip_lengths(clean_boundaries, duration_seconds=clean_duration)
    cut_count = len(clean_boundaries)

    if clean_duration > 0:
        cuts_per_minute = round(cut_count / (clean_duration / 60.0), 6)
    else:
        cuts_per_minute = 0.0

    if clip_lengths:
        median_clip_seconds = round(float(statistics.median(clip_lengths)), 6)
    else:
        median_clip_seconds = 0.0

    return PacingMetricsResult(
        cut_count=cut_count,
        cuts_per_minute=cuts_per_minute,
        median_clip_seconds=median_clip_seconds,
        clip_length_histogram_bins=build_clip_length_histogram(clip_lengths),
    ).to_dict()


def normalize_boundaries(
    boundaries_seconds: list[float] | tuple[float, ...],
    *,
    duration_seconds: float,
) -> list[float]:
    """Return sorted unique boundary values inside the media duration."""

    clean_duration = _safe_non_negative_float(duration_seconds)
    normalized: set[float] = set()

    for raw_value in boundaries_seconds or []:
        value = _safe_non_negative_float(raw_value)
        rounded = round(value, 3)

        if rounded <= 0:
            continue
        if clean_duration > 0 and rounded >= clean_duration:
            continue

        normalized.add(rounded)

    return sorted(normalized)


def build_clip_lengths(
    boundaries_seconds: list[float] | tuple[float, ...],
    *,
    duration_seconds: float,
) -> list[float]:
    """Convert scene boundaries into deterministic clip lengths."""

    clean_duration = _safe_non_negative_float(duration_seconds)
    if clean_duration <= 0:
        return []

    clean_boundaries = normalize_boundaries(
        list(boundaries_seconds),
        duration_seconds=clean_duration,
    )

    points = [0.0, *clean_boundaries, clean_duration]
    lengths: list[float] = []

    for start, end in zip(points, points[1:]):
        length = round(max(end - start, 0.0), 6)
        if length > 0:
            lengths.append(length)

    return lengths


def build_clip_length_histogram(
    clip_lengths: list[float] | tuple[float, ...],
) -> list[dict[str, Any]]:
    """Build deterministic histogram bins for clip length distribution."""

    clean_lengths = [_safe_non_negative_float(value) for value in clip_lengths or []]
    histogram: list[dict[str, Any]] = []

    for label, lower, upper in _DEFAULT_HISTOGRAM_BINS:
        count = 0
        for value in clean_lengths:
            if upper is None:
                if value >= lower:
                    count += 1
            elif lower <= value < upper:
                count += 1

        histogram.append(
            {
                "label": label,
                "min_seconds": lower,
                "max_seconds": upper,
                "count": count,
            }
        )

    return histogram


def _safe_non_negative_float(value: Any) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return 0.0

    if converted < 0:
        return 0.0

    return converted
