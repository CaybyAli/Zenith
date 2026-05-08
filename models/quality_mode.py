from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class QualityMode(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    PRO = "pro"
    CINEMATIC = "cinematic"


@dataclass
class QualityModeConfig:
    mode: QualityMode
    analysis_depth: str
    max_analysis_passes: int
    allow_overnight_render: bool
    min_confidence_threshold: float
    description: str


QUALITY_MODE_CONFIGS: dict[QualityMode, QualityModeConfig] = {
    QualityMode.FAST: QualityModeConfig(
        mode=QualityMode.FAST,
        analysis_depth="surface",
        max_analysis_passes=1,
        allow_overnight_render=False,
        min_confidence_threshold=0.5,
        description="Schnelle Analyse, weniger Tiefe. Für schnelle Drafts.",
    ),
    QualityMode.BALANCED: QualityModeConfig(
        mode=QualityMode.BALANCED,
        analysis_depth="standard",
        max_analysis_passes=2,
        allow_overnight_render=False,
        min_confidence_threshold=0.65,
        description="Solider Standard. Gutes Verhältnis aus Geschwindigkeit und Qualität.",
    ),
    QualityMode.PRO: QualityModeConfig(
        mode=QualityMode.PRO,
        analysis_depth="deep",
        max_analysis_passes=4,
        allow_overnight_render=False,
        min_confidence_threshold=0.80,
        description="Tiefe Analyse. Für wichtige Videos. Dauert länger.",
    ),
    QualityMode.CINEMATIC: QualityModeConfig(
        mode=QualityMode.CINEMATIC,
        analysis_depth="maximum",
        max_analysis_passes=8,
        allow_overnight_render=True,
        min_confidence_threshold=0.92,
        description="Maximale Qualität. Darf über Nacht laufen. Lieber langsam als schlecht.",
    ),
}


def get_quality_mode_config(mode: QualityMode) -> QualityModeConfig:
    return QUALITY_MODE_CONFIGS[mode]
