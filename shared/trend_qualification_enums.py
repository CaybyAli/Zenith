from enum import Enum


class ContentShape(str, Enum):
    REACTION_DRIVEN = "reaction_driven"
    TOPIC_DRIVEN = "topic_driven"
    NEWS_DRIVEN = "news_driven"
    CLIP_DRIVEN = "clip_driven"
    SEARCH_DRIVEN = "search_driven"
    UNKNOWN = "unknown"


class LifespanClass(str, Enum):
    FLASH = "flash"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class DecisionHint(str, Enum):
    BLOCK = "block"
    WATCH = "watch"
    KEEP = "keep"