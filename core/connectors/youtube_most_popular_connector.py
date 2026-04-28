from __future__ import annotations

import json
from datetime import datetime, timezone
from math import log10
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from core.trend_source_connector import TrendSourceConnector
from shared.errors import ValidationError


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


class YouTubeMostPopularConnector(TrendSourceConnector):
    connector_name = "youtube_most_popular"
    base_url = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(
        self,
        *,
        api_key: str,
        region_code: str = "DE",
        video_category_id: str | None = None,
        max_results: int = 10,
        timeout_seconds: int = 20,
        strict_category_match: bool | None = None,
    ) -> None:
        self.api_key = _clean_text(api_key)
        self.region_code = _clean_text(region_code, "DE").upper()
        self.video_category_id = _clean_text(video_category_id) or None
        self.max_results = max(1, min(50, int(max_results)))
        self.timeout_seconds = max(5, int(timeout_seconds))

        if strict_category_match is None:
            self.strict_category_match = self.video_category_id is not None
        else:
            self.strict_category_match = bool(strict_category_match)

        if not self.api_key:
            raise ValidationError("YouTube API key is required")

        if len(self.region_code) != 2:
            raise ValidationError("region_code must be a 2-letter country code")

        self.last_fetch_stats: dict[str, Any] = {
            "raw_count": 0,
            "mapped_count": 0,
            "skipped_count": 0,
            "skipped_items": [],
        }

    def fetch_items(self) -> list[dict[str, Any]]:
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": self.region_code,
            "maxResults": str(self.max_results),
            "key": self.api_key,
        }

        if self.video_category_id:
            params["videoCategoryId"] = self.video_category_id

        request_url = f"{self.base_url}?{urlencode(params)}"
        request = Request(
            request_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Zenith/1.0",
            },
        )

        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        items = payload.get("items", [])
        fetched_at = utc_now_iso()

        mapped_items: list[dict[str, Any]] = []
        skipped_items: list[dict[str, Any]] = []

        for item in items:
            include_item, skip_reason = self._should_include_item(item)
            if not include_item:
                skipped_items.append(self._build_skip_entry(item, skip_reason))
                continue

            mapped = self._map_item(item=item, fetched_at=fetched_at)
            if mapped:
                mapped_items.append(mapped)

        self.last_fetch_stats = {
            "raw_count": len(items),
            "mapped_count": len(mapped_items),
            "skipped_count": len(skipped_items),
            "skipped_items": skipped_items,
        }

        return mapped_items

    def _should_include_item(self, item: dict[str, Any]) -> tuple[bool, str | None]:
        if not self.strict_category_match:
            return True, None

        if not self.video_category_id:
            return True, None

        snippet = dict(item.get("snippet", {}))
        item_category_id = _clean_text(snippet.get("categoryId")) or None

        if item_category_id != self.video_category_id:
            return False, "category_mismatch"

        return True, None

    def _build_skip_entry(
        self,
        item: dict[str, Any],
        reason: str | None,
    ) -> dict[str, Any]:
        snippet = dict(item.get("snippet", {}))

        return {
            "reason": reason or "unknown",
            "external_id": _clean_text(item.get("id")) or None,
            "title": _clean_text(snippet.get("title")) or None,
            "category_id": _clean_text(snippet.get("categoryId")) or None,
        }

    def _map_item(
        self,
        *,
        item: dict[str, Any],
        fetched_at: str,
    ) -> dict[str, Any] | None:
        snippet = dict(item.get("snippet", {}))
        statistics = dict(item.get("statistics", {}))

        title = _clean_text(snippet.get("title"))
        if not title:
            return None

        youtube_video_id = _clean_text(item.get("id"))
        published_at = _clean_text(snippet.get("publishedAt")) or fetched_at
        category_id = _clean_text(snippet.get("categoryId")) or self.video_category_id or None

        signal_strength = self._derive_signal_strength(statistics)
        competition_density = self._derive_competition_density(
            statistics=statistics,
            category_id=category_id,
        )
        confidence = 0.90

        return {
            "title": title,
            "topic": title,
            "platform": "youtube",
            "observed_at": published_at,
            "captured_at": fetched_at,
            "signal_strength": signal_strength,
            "competition_density": competition_density,
            "confidence": confidence,
            "language": (
                _clean_text(snippet.get("defaultAudioLanguage"))
                or _clean_text(snippet.get("defaultLanguage"))
                or None
            ),
            "channel_targets": self._derive_channel_targets(category_id),
            "external_source": self.connector_name,
            "external_id": youtube_video_id,
            "source_channel_title": _clean_text(snippet.get("channelTitle")) or None,
            "youtube_video_id": youtube_video_id,
            "youtube_category_id": category_id,
            "youtube_statistics": {
                "viewCount": _safe_int(statistics.get("viewCount")),
                "likeCount": _safe_int(statistics.get("likeCount")),
                "commentCount": _safe_int(statistics.get("commentCount")),
            },
            "youtube_region_code": self.region_code,
        }

    def _derive_signal_strength(self, statistics: dict[str, Any]) -> float:
        views = _safe_int(statistics.get("viewCount"))
        likes = _safe_int(statistics.get("likeCount"))
        comments = _safe_int(statistics.get("commentCount"))

        view_score = min(1.0, log10(views + 1) / 7.0)
        engagement_raw = (likes + (comments * 2)) / max(views, 1)
        engagement_score = min(1.0, engagement_raw * 50.0)

        score = (0.70 * view_score) + (0.30 * engagement_score)
        return round(max(0.0, min(1.0, score)), 4)

    def _derive_competition_density(
        self,
        *,
        statistics: dict[str, Any],
        category_id: str | None,
    ) -> float:
        views = _safe_int(statistics.get("viewCount"))

        base = 0.70
        if category_id == "20":
            base = 0.78

        if views >= 5_000_000:
            base += 0.08
        elif views >= 1_000_000:
            base += 0.04

        return round(max(0.0, min(1.0, base)), 4)

    def _derive_channel_targets(self, category_id: str | None) -> list[str]:
        if category_id == "20":
            return ["main", "uncut", "faceless"]

        return ["main", "faceless"]