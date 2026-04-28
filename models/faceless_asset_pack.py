from dataclasses import dataclass
from typing import List


@dataclass
class FacelessAssetPack:
    job_id: str
    script_text: str
    voiceover_source: str
    scene_visual_plan: List[str]
    music_plan: str
    text_overlay_plan: List[str]
    asset_pack_confidence: float