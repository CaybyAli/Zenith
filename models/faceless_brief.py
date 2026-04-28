from dataclasses import dataclass
from typing import List


@dataclass
class FacelessBrief:
    job_id: str
    topic: str
    angle: str
    format_type: str
    target_runtime: float
    hook_direction: str
    scene_plan: List[str]
    voiceover_style: str
    visual_style: str
    brief_confidence: float