from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping


INTENSITY_RANK = {
    "none": 0,
    "medium": 2,
    "high": 3,
}


@dataclass(frozen=True)
class AdaptiveReactionProfile:
    mode: str
    candidate_count: int
    medium_fusion_score: float
    high_fusion_score: float
    medium_mic_rise_db: float
    high_mic_rise_db: float
    medium_percentile: float
    high_percentile: float
    mic_floor_percentile: float
    fusion_mean: float
    fusion_std: float
    fusion_p50: float
    fusion_p75: float
    fusion_p90: float
    fusion_p95: float
    mic_rise_p50: float
    mic_rise_p75: float
    mic_rise_p90: float
    mic_rise_p95: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return round(ordered[0], 6)

    pct = max(0.0, min(100.0, float(pct)))
    pos = (len(ordered) - 1) * (pct / 100.0)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))

    if lo == hi:
        return round(ordered[lo], 6)

    weight = pos - lo
    value = ordered[lo] + ((ordered[hi] - ordered[lo]) * weight)
    return round(value, 6)


def mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0

    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return round(mean, 6), round(math.sqrt(variance), 6)


def _value(row: Mapping[str, Any], key: str) -> float:
    return _safe_float(row.get(key), 0.0)


def build_adaptive_reaction_profile(
    candidate_rows: list[Mapping[str, Any]],
    *,
    medium_percentile: float = 90.0,
    high_percentile: float = 97.0,
    mic_floor_percentile: float = 95.0,
) -> AdaptiveReactionProfile:
    """
    Mic-primary adaptive profile.

    Wichtig:
    - mic_floor_percentile ist der eigentliche Reaction-Gate.
    - fusion_score darf nur eine stimmlich erhöhte Reaktion bestätigen/verstärken.
    - Hohe Facecam/Fusion allein erzeugt KEINE Reaktion.
    """
    if not candidate_rows:
        raise ValueError("candidate_rows must not be empty")

    fusion_values = [_value(row, "fusion_score") for row in candidate_rows]
    mic_values = [_value(row, "mic_audio_rise_db") for row in candidate_rows]

    fusion_mean, fusion_std = mean_std(fusion_values)

    medium_fusion = percentile(fusion_values, medium_percentile)
    high_fusion = max(
        medium_fusion + 0.001,
        percentile(fusion_values, high_percentile),
    )

    medium_mic = percentile(mic_values, mic_floor_percentile)
    high_mic = max(
        medium_mic + 0.001,
        percentile(mic_values, max(mic_floor_percentile, 98.0)),
    )

    return AdaptiveReactionProfile(
        mode="per_video_adaptive_mic_primary_reaction_gate",
        candidate_count=len(candidate_rows),
        medium_fusion_score=round(medium_fusion, 6),
        high_fusion_score=round(high_fusion, 6),
        medium_mic_rise_db=round(medium_mic, 6),
        high_mic_rise_db=round(high_mic, 6),
        medium_percentile=float(medium_percentile),
        high_percentile=float(high_percentile),
        mic_floor_percentile=float(mic_floor_percentile),
        fusion_mean=fusion_mean,
        fusion_std=fusion_std,
        fusion_p50=percentile(fusion_values, 50),
        fusion_p75=percentile(fusion_values, 75),
        fusion_p90=percentile(fusion_values, 90),
        fusion_p95=percentile(fusion_values, 95),
        mic_rise_p50=percentile(mic_values, 50),
        mic_rise_p75=percentile(mic_values, 75),
        mic_rise_p90=percentile(mic_values, 90),
        mic_rise_p95=percentile(mic_values, 95),
    )


def classify_adaptive_reaction(
    row: Mapping[str, Any],
    profile: AdaptiveReactionProfile,
) -> str:
    fusion = _value(row, "fusion_score")
    mic_rise = _value(row, "mic_audio_rise_db")

    # MIC-PRIMARY HARD GATE:
    # Ohne erhöhte Stimme gibt es keine Reaction, egal wie hoch Facecam/Fusion ist.
    if mic_rise < profile.medium_mic_rise_db:
        return "none"

    # Fusion ist nur sekundäre Bestätigung, damit reine Mic-Artefakte nicht sofort triggern.
    if fusion < profile.medium_fusion_score:
        return "none"

    if mic_rise >= profile.high_mic_rise_db and fusion >= profile.high_fusion_score:
        return "high"

    return "medium"


def reaction_rank(intensity: str) -> int:
    return INTENSITY_RANK.get(str(intensity).lower(), 0)


def is_medium_or_high(intensity: str) -> bool:
    return reaction_rank(intensity) >= INTENSITY_RANK["medium"]
