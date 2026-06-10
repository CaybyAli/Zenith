from __future__ import annotations

from dataclasses import dataclass

CONTENT_TYPE_GAMING_MAIN = "gaming_main"
CONTENT_TYPE_VLOG_MAIN = "vlog_main"
CONTENT_TYPE_UNCUT = "uncut"

CATEGORY_INTRO = "intro"
CATEGORY_OUTRO = "outro"
CATEGORY_VLOG_BACKGROUND = "vlog_background"
CATEGORY_FUNNY_GAMING_BACKGROUND = "funny_gaming_background"
CATEGORY_FAIL = "fail"
CATEGORY_HYPE = "hype"
CATEGORY_SAD = "sad"
CATEGORY_NONE = "none"

ALL_CONTENT_TYPES = (
    CONTENT_TYPE_GAMING_MAIN,
    CONTENT_TYPE_VLOG_MAIN,
    CONTENT_TYPE_UNCUT,
)

ALL_MUSIC_CATEGORIES = (
    CATEGORY_INTRO,
    CATEGORY_OUTRO,
    CATEGORY_VLOG_BACKGROUND,
    CATEGORY_FUNNY_GAMING_BACKGROUND,
    CATEGORY_FAIL,
    CATEGORY_HYPE,
    CATEGORY_SAD,
    CATEGORY_NONE,
)

_ALLOWED_BY_CONTENT_TYPE = {
    CONTENT_TYPE_GAMING_MAIN: frozenset(
        (
            CATEGORY_INTRO,
            CATEGORY_OUTRO,
            CATEGORY_FUNNY_GAMING_BACKGROUND,
            CATEGORY_FAIL,
            CATEGORY_HYPE,
            CATEGORY_SAD,
        )
    ),
    CONTENT_TYPE_VLOG_MAIN: frozenset(
        (
            CATEGORY_INTRO,
            CATEGORY_OUTRO,
            CATEGORY_VLOG_BACKGROUND,
            CATEGORY_SAD,
        )
    ),
    CONTENT_TYPE_UNCUT: frozenset((CATEGORY_NONE,)),
}

_DEFAULT_PREVIEW_CATEGORY_BY_CONTENT_TYPE = {
    CONTENT_TYPE_GAMING_MAIN: CATEGORY_FUNNY_GAMING_BACKGROUND,
    CONTENT_TYPE_VLOG_MAIN: CATEGORY_VLOG_BACKGROUND,
    CONTENT_TYPE_UNCUT: CATEGORY_NONE,
}


@dataclass(frozen=True)
class MusicContentTypePolicyError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


def normalize_content_type(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in ALL_CONTENT_TYPES:
        raise MusicContentTypePolicyError(f"unknown content_type blocked: {value}")
    return normalized


def _normalize_category(category: str) -> str:
    normalized = str(category).strip().lower()
    if normalized not in ALL_MUSIC_CATEGORIES:
        raise MusicContentTypePolicyError(f"unknown music category blocked: {category}")
    return normalized


def get_allowed_music_categories(content_type: str) -> tuple[str, ...]:
    normalized_content_type = normalize_content_type(content_type)
    return tuple(sorted(_ALLOWED_BY_CONTENT_TYPE[normalized_content_type]))


def is_music_category_allowed_for_content_type(content_type: str, category: str) -> bool:
    normalized_content_type = normalize_content_type(content_type)
    normalized_category = _normalize_category(category)
    return normalized_category in _ALLOWED_BY_CONTENT_TYPE[normalized_content_type]


def validate_music_category_for_content_type(content_type: str, category: str) -> str:
    normalized_content_type = normalize_content_type(content_type)
    normalized_category = _normalize_category(category)
    if normalized_category not in _ALLOWED_BY_CONTENT_TYPE[normalized_content_type]:
        raise MusicContentTypePolicyError(
            f"music category {normalized_category} blocked for content_type {normalized_content_type}"
        )
    return normalized_category


def choose_default_preview_category_for_content_type(content_type: str) -> str:
    normalized_content_type = normalize_content_type(content_type)
    return _DEFAULT_PREVIEW_CATEGORY_BY_CONTENT_TYPE[normalized_content_type]
