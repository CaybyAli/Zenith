from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import log10
from typing import Any
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


def _strip_tag(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_datetime_or_now(value: Any) -> str:
    text = _clean_text(value)
    if not text:
        return utc_now_iso()

    try:
        dt = parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return utc_now_iso()


def _find_first_text(element: ET.Element, local_names: set[str]) -> str | None:
    for child in element.iter():
        if _strip_tag(child.tag) in local_names:
            text = _clean_text(child.text)
            if text:
                return text
    return None


class GoogleTrendsRssConnector(TrendSourceConnector):
    connector_name = "google_trends_rss"

    def __init__(
        self,
        *,
        rss_url: str,
        country_code: str = "DE",
        timeout_seconds: int = 20,
        default_signal_strength: float = 0.68,
        default_competition_density: float = 0.58,
        default_confidence: float = 0.85,
    ) -> None:
        self.rss_url = _clean_text(rss_url)
        self.country_code = _clean_text(country_code, "DE").upper()
        self.timeout_seconds = max(5, int(timeout_seconds))
        self.default_signal_strength = max(0.0, min(1.0, float(default_signal_strength)))
        self.default_competition_density = max(0.0, min(1.0, float(default_competition_density)))
        self.default_confidence = max(0.0, min(1.0, float(default_confidence)))

        if not self.rss_url:
            raise ValidationError("Google Trends RSS URL is required")

        if not self.rss_url.startswith(("http://", "https://")):
            raise ValidationError("rss_url must start with http:// or https://")

        if len(self.country_code) != 2:
            raise ValidationError("country_code must be a 2-letter country code")

        self.last_fetch_stats: dict[str, Any] = {
            "raw_count": 0,
            "mapped_count": 0,
            "skipped_count": 0,
            "skipped_items": [],
        }

    def fetch_items(self) -> list[dict[str, Any]]:
        request = Request(
            self.rss_url,
            headers={
                "Accept": "application/rss+xml, application/xml, text/xml",
                "User-Agent": "Zenith/1.0",
            },
        )

        with urlopen(request, timeout=self.timeout_seconds) as response:
            xml_bytes = response.read()

        root = ET.fromstring(xml_bytes)
        fetched_at = utc_now_iso()

        raw_count = 0
        mapped_items: list[dict[str, Any]] = []
        skipped_items: list[dict[str, Any]] = []

        for item in root.iter():
            if _strip_tag(item.tag) != "item":
                continue

            raw_count += 1
            mapped = self._map_item(item=item, fetched_at=fetched_at)

            if mapped is None:
                skipped_items.append(
                    {
                        "reason": "missing_title",
                        "title": _find_first_text(item, {"title"}),
                        "link": _find_first_text(item, {"link"}),
                    }
                )
                continue

            mapped_items.append(mapped)

        self.last_fetch_stats = {
            "raw_count": raw_count,
            "mapped_count": len(mapped_items),
            "skipped_count": len(skipped_items),
            "skipped_items": skipped_items,
        }

        return mapped_items

    def _map_item(
        self,
        *,
        item: ET.Element,
        fetched_at: str,
    ) -> dict[str, Any] | None:
        title = _find_first_text(item, {"title"})
        if not _clean_text(title):
            return None

        link = _find_first_text(item, {"link"})
        description = _find_first_text(item, {"description"})
        pub_date = _parse_datetime_or_now(_find_first_text(item, {"pubDate", "published", "updated"}))
        approx_traffic = _find_first_text(item, {"approx_traffic"})
        news_item_title = _find_first_text(item, {"news_item_title"})
        news_item_source = _find_first_text(item, {"news_item_source"})

        signal_strength = self._derive_signal_strength(approx_traffic)
        external_id = self._build_external_id(
            title=title,
            pub_date=pub_date,
            news_item_title=news_item_title,
        )

        return {
            "title": title,
            "topic": title,
            "platform": "web",
            "observed_at": pub_date,
            "captured_at": fetched_at,
            "signal_strength": signal_strength,
            "competition_density": self.default_competition_density,
            "confidence": self.default_confidence,
            "language": None,
            "channel_targets": [],
            "external_source": self.connector_name,
            "external_id": external_id,
            "external_link": _clean_text(link) or None,
            "google_trends_country_code": self.country_code,
            "google_trends_approx_traffic": _clean_text(approx_traffic) or None,
            "google_trends_description": _clean_text(description) or None,
            "google_trends_news_item_title": _clean_text(news_item_title) or None,
            "google_trends_news_item_source": _clean_text(news_item_source) or None,
        }

    def _build_external_id(
        self,
        *,
        title: str,
        pub_date: str,
        news_item_title: str | None,
    ) -> str:
        safe_title = _clean_text(title, "untitled").lower().replace("|", " ").strip()
        safe_news_title = _clean_text(news_item_title).lower().replace("|", " ").strip()

        parts = [
            self.country_code,
            safe_title,
            pub_date,
        ]

        if safe_news_title:
            parts.append(safe_news_title)

        return "|".join(parts)

    def _derive_signal_strength(self, approx_traffic: str | None) -> float:
        text = _clean_text(approx_traffic).upper().replace("+", "").replace(",", "").strip()
        if not text:
            return round(self.default_signal_strength, 4)

        multiplier = 1
        if text.endswith("K"):
            multiplier = 1_000
            text = text[:-1]
        elif text.endswith("M"):
            multiplier = 1_000_000
            text = text[:-1]
        elif text.endswith("B"):
            multiplier = 1_000_000_000
            text = text[:-1]

        try:
            traffic_value = float(text) * multiplier
        except ValueError:
            return round(self.default_signal_strength, 4)

        traffic_score = min(1.0, log10(traffic_value + 1) / 8.0)
        score = max(self.default_signal_strength, traffic_score)
        return round(max(0.0, min(1.0, score)), 4)