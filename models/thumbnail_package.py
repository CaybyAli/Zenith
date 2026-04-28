from dataclasses import dataclass
from typing import List


@dataclass
class ThumbnailPackage:
    job_id: str
    selected_thumbnail: str
    thumbnail_variants: List[str]
    thumbnail_scores: List[float]
    selected_index: int