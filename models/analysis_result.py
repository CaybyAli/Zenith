from dataclasses import dataclass
from typing import List


@dataclass
class AnalysisResult:
    job_id: str
    duration_seconds: float
    file_size_bytes: int
    usable_for_shorts: bool
    usable_for_longform: bool
    analysis_confidence: float
    notes: List[str]