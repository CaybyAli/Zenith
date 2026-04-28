from dataclasses import dataclass
from typing import List


@dataclass
class MetadataPackage:
    job_id: str
    description: str
    hashtags: List[str]