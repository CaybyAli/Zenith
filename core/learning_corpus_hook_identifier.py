from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


HOOK_PATTERN_CLASSES = {"question", "statement", "action", "name_drop", "unknown"}

_QUESTION_STARTERS = {
    "wer", "was", "wann", "wo", "warum", "wieso", "weshalb", "wie",
    "who", "what", "when", "where", "why", "how",
    "can", "could", "do", "does", "did", "is", "are", "will",
}

_ACTION_STARTERS = {
    "schau", "schaut", "guck", "guckt", "komm", "kommt", "hör", "hört",
    "passt", "pass", "warte", "wartet", "stell", "stellt", "mach", "macht",
    "watch", "look", "listen", "check", "see", "imagine", "wait", "come",
}

_NAME_DROP_PREFIXES = {
    "herr", "frau", "mr", "mrs", "ms", "dr", "prof",
}

_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9][A-Za-zÄÖÜäöüß0-9'_-]*")


@dataclass(frozen=True)
class HookIdentifierResult:
    """Stable hook payload used by style_fingerprint.json."""

    first_words: str
    pattern_class: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def identify_hook(
    transcript: str | dict[str, Any] | None,
    *,
    max_words: int = 12,
) -> dict[str, Any]:
    """
    Classify the first 5-10 seconds of transcript text.

    Output schema:
    - first_words
    - pattern_class: question | statement | action | name_drop | unknown
    """

    if max_words <= 0:
        raise ValueError("max_words must be greater than zero")

    text = extract_hook_text(transcript)
    words = extract_words(text)
    first_words = " ".join(words[:max_words])
    pattern_class = classify_hook_pattern(text, words)

    return HookIdentifierResult(
        first_words=first_words,
        pattern_class=pattern_class,
    ).to_dict()


def extract_hook_text(transcript: str | dict[str, Any] | None) -> str:
    """Accept either raw text or the transcript module output dict."""

    if transcript is None:
        return ""

    if isinstance(transcript, dict):
        value = transcript.get("first_10s_text", "")
    else:
        value = transcript

    return normalize_text(str(value or ""))


def classify_hook_pattern(text: str, words: list[str] | tuple[str, ...] | None = None) -> str:
    """Return one deterministic hook pattern class."""

    clean_text = normalize_text(text)
    clean_words = list(words) if words is not None else extract_words(clean_text)

    if not clean_text or not clean_words:
        return "unknown"

    first_word = clean_words[0].lower()

    if "?" in clean_text or first_word in _QUESTION_STARTERS:
        return "question"

    if first_word in _ACTION_STARTERS:
        return "action"

    if has_name_drop(clean_words):
        return "name_drop"

    if len(clean_words) >= 3:
        return "statement"

    return "unknown"


def has_name_drop(words: list[str] | tuple[str, ...]) -> bool:
    """
    Detect lightweight name-drop patterns without a model.

    This intentionally uses only deterministic text heuristics:
    - known title prefixes followed by another word
    - two adjacent capitalized words
    - one capitalized non-initial word
    """

    if not words:
        return False

    lowered = [word.lower().strip(".,:;!?") for word in words]
    for index, word in enumerate(lowered[:-1]):
        if word in _NAME_DROP_PREFIXES:
            return True

    capitalized_flags = [_looks_like_name_token(word) for word in words]

    for left, right in zip(capitalized_flags, capitalized_flags[1:]):
        if left and right:
            return True

    for index, is_capitalized in enumerate(capitalized_flags):
        if index > 0 and is_capitalized:
            return True

    return False


def extract_words(text: str) -> list[str]:
    """Extract deterministic word tokens from transcript text."""

    return [match.group(0).strip() for match in _WORD_RE.finditer(text or "") if match.group(0).strip()]


def normalize_text(value: str) -> str:
    """Normalize whitespace without changing wording."""

    return " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())


def _looks_like_name_token(word: str) -> bool:
    clean = str(word or "").strip(".,:;!?()[]{}\"'")
    if len(clean) < 2:
        return False

    if clean.isupper():
        return False

    first = clean[0]
    rest = clean[1:]

    return first.isupper() and any(char.islower() for char in rest)
