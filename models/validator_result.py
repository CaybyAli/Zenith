from dataclasses import dataclass
from typing import List


@dataclass
class ValidatorResult:
    job_id: str
    validator_status: str
    blocking_issues: List[str]
    warnings: List[str]
    ready_for_publish: bool