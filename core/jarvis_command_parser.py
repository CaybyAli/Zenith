from __future__ import annotations

import re

from models.jarvis_command import JarvisCommand
from shared.jarvis_enums import JarvisCommandType


class JarvisCommandParser:
    def parse(self, raw_text: str) -> JarvisCommand:
        normalized_query = self._normalize_text(raw_text)
        command_type = self._detect_command_type(normalized_query)

        return JarvisCommand(
            raw_text=raw_text,
            command_type=command_type,
            normalized_query=normalized_query,
            filters={},
            requested_scope=None,
        )

    def _normalize_text(self, value: str) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text

    def _detect_command_type(self, normalized_query: str) -> JarvisCommandType:
        if not normalized_query:
            return JarvisCommandType.UNKNOWN

        if self._contains_any(
            normalized_query,
            [
                "systemstatus",
                "system status",
                "wie ist der systemstatus",
                "gesamtstatus",
                "gesamt lage",
                "gesamtlage",
            ],
        ):
            return JarvisCommandType.SYSTEM_STATUS

        if self._contains_any(
            normalized_query,
            [
                "review",
                "review status",
                "was muss ich reviewen",
                "was muss ich heute reviewen",
                "offene reviews",
                "review fälle",
            ],
        ):
            return JarvisCommandType.REVIEW_STATUS

        if self._contains_any(
            normalized_query,
            [
                "blockiert",
                "blocked jobs",
                "welche jobs sind blockiert",
                "blockierte jobs",
            ],
        ):
            return JarvisCommandType.BLOCKED_JOBS

        if self._contains_any(
            normalized_query,
            [
                "warnfälle",
                "warnfaelle",
                "warning cases",
                "warnungen",
                "zeig mir warnfälle",
                "zeig mir warnungen",
            ],
        ):
            return JarvisCommandType.WARNING_CASES

        if self._contains_any(
            normalized_query,
            [
                "queue",
                "queue status",
                "warteschlange",
            ],
        ):
            return JarvisCommandType.QUEUE_STATUS

        if self._contains_any(
            normalized_query,
            [
                "publish",
                "publish status",
                "publishing",
                "veröffentlicht",
                "veroeffentlicht",
            ],
        ):
            return JarvisCommandType.PUBLISH_STATUS

        if self._contains_any(
            normalized_query,
            [
                "kpi",
                "performance",
                "was läuft gerade am besten",
                "was laeuft gerade am besten",
                "top performer",
            ],
        ):
            return JarvisCommandType.KPI_SUMMARY

        if self._contains_any(
            normalized_query,
            [
                "schwache plattform",
                "schwache plattformen",
                "weak platform",
                "weak platforms",
                "welche plattform ist schwach",
                "welche plattformen sind schwach",
            ],
        ):
            return JarvisCommandType.WEAK_PLATFORMS

        if self._contains_any(
            normalized_query,
            [
                "feedback",
                "feedback summary",
                "was sagt das feedback",
                "feedback lage",
            ],
        ):
            return JarvisCommandType.FEEDBACK_SUMMARY

        if self._contains_any(
            normalized_query,
            [
                "runtime",
                "runtime status",
                "runtime mode",
            ],
        ):
            return JarvisCommandType.RUNTIME_STATUS

        if self._contains_any(
            normalized_query,
            [
                "vacation",
                "vacation status",
                "urlaub",
                "urlaubsmode",
                "vacation mode",
            ],
        ):
            return JarvisCommandType.VACATION_STATUS

        if self._contains_any(
            normalized_query,
            [
                "maintenance",
                "maintenance status",
                "cleanup status",
                "recovery status",
            ],
        ):
            return JarvisCommandType.MAINTENANCE_STATUS

        return JarvisCommandType.UNKNOWN

    def _contains_any(self, normalized_query: str, candidates: list[str]) -> bool:
        return any(candidate in normalized_query for candidate in candidates)