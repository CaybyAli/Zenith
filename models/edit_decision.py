from dataclasses import dataclass
from typing import List


@dataclass
class EditDecision:
    job_id: str
    selected_segments: List[str]
    removed_segments: List[str]
    target_runtime: float
    hook_candidate_range: str
    cut_style: str
    cut_confidence: float