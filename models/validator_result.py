from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class ValidatorResult:
    job_id: str
    validator_status: str
    blocking_issues: List[str]
    warnings: List[str]
    ready_for_publish: bool
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)
