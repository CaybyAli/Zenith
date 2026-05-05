from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HookSentence:
    text: str
    score: float
    reason: str
    start_seconds: Optional[float] = None
    end_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "score": self.score,
            "reason": self.reason,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
        }


@dataclass
class HookKeywordResult:
    keywords: list[str] = field(default_factory=list)
    hook_sentences: list[HookSentence] = field(default_factory=list)
    top_hook: Optional[str] = None
    engine: str = "rule-based-hook-keyword-v1"
    source_text_length: int = 0

    def to_dict(self) -> dict:
        return {
            "keywords": list(self.keywords),
            "hook_sentences": [
                hook_sentence.to_dict()
                for hook_sentence in self.hook_sentences
            ],
            "top_hook": self.top_hook,
            "engine": self.engine,
            "source_text_length": self.source_text_length,
        }
