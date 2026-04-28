from dataclasses import dataclass


@dataclass
class SubtitleAsset:
    job_id: str
    text: str
    language: str
    confidence: float