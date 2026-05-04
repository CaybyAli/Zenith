from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str
    confidence: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "text": self.text,
            "confidence": self.confidence,
        }


@dataclass
class TranscriptResult:
    source_path: str
    language: Optional[str]
    segments: list[TranscriptSegment]
    full_text: str
    engine: str

    def to_dict(self) -> dict:
        return {
            "source_path": self.source_path,
            "language": self.language,
            "segments": [segment.to_dict() for segment in self.segments],
            "full_text": self.full_text,
            "engine": self.engine,
        }