from dataclasses import dataclass


@dataclass
class PublishDecision:
    job_id: str
    decision: str
    reason: str