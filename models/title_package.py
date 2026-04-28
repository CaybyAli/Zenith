from dataclasses import dataclass
from typing import List


@dataclass
class TitlePackage:
    job_id: str
    primary_title: str
    backup_titles: List[str]
    title_score: float