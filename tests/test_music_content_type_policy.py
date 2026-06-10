from __future__ import annotations

import pytest

from core.music_content_type_policy import (
    CATEGORY_FAIL,
    CATEGORY_FUNNY_GAMING_BACKGROUND,
    CATEGORY_HYPE,
    CATEGORY_NONE,
    CATEGORY_VLOG_BACKGROUND,
    CONTENT_TYPE_GAMING_MAIN,
    CONTENT_TYPE_UNCUT,
    CONTENT_TYPE_VLOG_MAIN,
    MusicContentTypePolicyError,
    choose_default_preview_category_for_content_type,
    is_music_category_allowed_for_content_type,
    validate_music_category_for_content_type,
)


def test_gaming_main_allows_funny_gaming_background():
    assert is_music_category_allowed_for_content_type(
        CONTENT_TYPE_GAMING_MAIN,
        CATEGORY_FUNNY_GAMING_BACKGROUND,
    )


def test_gaming_main_allows_hype():
    assert is_music_category_allowed_for_content_type(CONTENT_TYPE_GAMING_MAIN, CATEGORY_HYPE)


def test_gaming_main_allows_fail():
    assert is_music_category_allowed_for_content_type(CONTENT_TYPE_GAMING_MAIN, CATEGORY_FAIL)


def test_gaming_main_blocks_vlog_background():
    assert not is_music_category_allowed_for_content_type(
        CONTENT_TYPE_GAMING_MAIN,
        CATEGORY_VLOG_BACKGROUND,
    )
    with pytest.raises(MusicContentTypePolicyError):
        validate_music_category_for_content_type(CONTENT_TYPE_GAMING_MAIN, CATEGORY_VLOG_BACKGROUND)


def test_vlog_main_allows_vlog_background():
    assert is_music_category_allowed_for_content_type(CONTENT_TYPE_VLOG_MAIN, CATEGORY_VLOG_BACKGROUND)


def test_vlog_main_blocks_funny_gaming_background():
    assert not is_music_category_allowed_for_content_type(
        CONTENT_TYPE_VLOG_MAIN,
        CATEGORY_FUNNY_GAMING_BACKGROUND,
    )


def test_vlog_main_blocks_hype():
    assert not is_music_category_allowed_for_content_type(CONTENT_TYPE_VLOG_MAIN, CATEGORY_HYPE)


def test_vlog_main_blocks_fail():
    assert not is_music_category_allowed_for_content_type(CONTENT_TYPE_VLOG_MAIN, CATEGORY_FAIL)


def test_uncut_blocks_every_music_category():
    for category in (
        CATEGORY_VLOG_BACKGROUND,
        CATEGORY_FUNNY_GAMING_BACKGROUND,
        CATEGORY_HYPE,
        CATEGORY_FAIL,
    ):
        assert not is_music_category_allowed_for_content_type(CONTENT_TYPE_UNCUT, category)


def test_uncut_allows_only_none():
    assert is_music_category_allowed_for_content_type(CONTENT_TYPE_UNCUT, CATEGORY_NONE)


def test_unknown_content_type_is_blocked():
    with pytest.raises(MusicContentTypePolicyError):
        is_music_category_allowed_for_content_type("unknown", CATEGORY_VLOG_BACKGROUND)


def test_default_preview_category_by_content_type():
    assert (
        choose_default_preview_category_for_content_type(CONTENT_TYPE_GAMING_MAIN)
        == CATEGORY_FUNNY_GAMING_BACKGROUND
    )
    assert choose_default_preview_category_for_content_type(CONTENT_TYPE_VLOG_MAIN) == CATEGORY_VLOG_BACKGROUND
    assert choose_default_preview_category_for_content_type(CONTENT_TYPE_UNCUT) == CATEGORY_NONE
