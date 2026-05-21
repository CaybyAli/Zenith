"""
P3-3F: But/Therefore Story Flow -> Timeline Segment Ordering.

Liest but_therefore_story-Signale und modifiziert die Score-Reihenfolge
von bereits gescorten Kandidaten in der _dedupe_and_select-Phase.
"""

from __future__ import annotations

import logging
from typing import Any

from core.timeline_signal_consumer import (
    SIGNAL_BUT_THEREFORE,
    TimelineSignalConsumer,
)

logger = logging.getLogger(__name__)

_SETUP_BONUS = 0.04
_CONFLICT_BONUS = 0.03
_PAYOFF_BONUS = 0.05
_AND_RUN_PENALTY = -0.04
_ORPHAN_REACTION_PENALTY = -0.05


def apply_story_flow_ordering(scored_candidates: list[dict], job: Any) -> list[dict]:
    """
    Wendet leichte But/Therefore-Story-Modulation auf selection_score an.

    - Kein Signal -> Original-Liste unveraendert zurueck.
    - Kein Loeschen von Kandidaten.
    - Orphan-Reactions werden nur niedriger priorisiert.
    - Protected/Continuity-Blocking-Signale werden nicht ueberstimmt.
    """
    if not scored_candidates or job is None:
        return scored_candidates

    try:
        consumer = TimelineSignalConsumer.from_job(job)
        bundle = consumer.read(SIGNAL_BUT_THEREFORE)
    except Exception as exc:
        logger.debug("[P3-3F-STORY] unavailable: %s", exc)
        return scored_candidates

    if not bundle.available:
        return scored_candidates

    adjusted: list[dict] = []
    and_run_count = 0

    for item in scored_candidates:
        if not isinstance(item, dict):
            adjusted.append(item)
            continue

        candidate = item.get("candidate")
        start, end = _candidate_bounds(candidate)
        if start is None or end is None:
            adjusted.append(item)
            continue

        story_signals = consumer.signals_for_segment(start, end, SIGNAL_BUT_THEREFORE)
        if not story_signals:
            adjusted.append(item)
            and_run_count = 0
            continue

        story_signal = _dominant_story_signal(story_signals)
        role = _story_role(story_signal)

        if role == "and":
            and_run_count += 1
        else:
            and_run_count = 0

        if _is_protected_or_continuity_blocked(story_signal):
            adjusted.append(item)
            continue

        modifier = 0.0
        notes: list[str] = []

        if role == "setup":
            modifier += _SETUP_BONUS
            notes.append("story_setup_bonus")
        elif role in {"but", "conflict"}:
            modifier += _CONFLICT_BONUS
            notes.append("story_conflict_bonus")
        elif role in {"therefore", "payoff"}:
            modifier += _PAYOFF_BONUS
            notes.append("story_payoff_bonus")

        if role == "and" and and_run_count > 2:
            modifier += _AND_RUN_PENALTY
            notes.append("story_and_run_penalty")

        if _is_orphan_reaction(story_signal):
            modifier += _ORPHAN_REACTION_PENALTY
            notes.append("story_orphan_reaction_penalty")

        if modifier == 0.0:
            adjusted.append(item)
            continue

        updated = dict(item)
        updated["selection_score"] = float(updated.get("selection_score", 0.0) or 0.0) + modifier
        if "score" in updated:
            updated["score"] = float(updated.get("score", 0.0) or 0.0) + modifier
        updated["notes"] = list(updated.get("notes") or []) + notes

        adjusted.append(updated)

    return adjusted


def _candidate_bounds(candidate: Any) -> tuple[float | None, float | None]:
    try:
        if hasattr(candidate, "start_time") and hasattr(candidate, "end_time"):
            return float(candidate.start_time), float(candidate.end_time)

        if isinstance(candidate, dict):
            start = candidate.get("start_time", candidate.get("start"))
            end = candidate.get("end_time", candidate.get("end"))
            if start is None or end is None:
                return None, None
            return float(start), float(end)
    except Exception:
        return None, None

    return None, None


def _dominant_story_signal(signals: list[dict]) -> dict:
    best_signal: dict = {}
    best_score = -1.0

    for signal in signals:
        if not isinstance(signal, dict):
            continue

        score = _story_signal_score(signal)
        if score > best_score:
            best_score = score
            best_signal = signal

    return best_signal


def _story_signal_score(signal: dict) -> float:
    for field in (
        "story_score",
        "signal_score",
        "score",
        "conflict_score",
        "consequence_score",
        "reaction_score",
        "neutral_score",
    ):
        try:
            if field in signal:
                return float(signal.get(field) or 0.0)
        except Exception:
            return 0.0
    return 0.0


def _story_role(signal: dict) -> str:
    return str(
        signal.get("story_role")
        or signal.get("role")
        or signal.get("moment_role")
        or ""
    ).strip().lower()


def _is_orphan_reaction(signal: dict) -> bool:
    return bool(
        signal.get("orphan_reaction")
        or signal.get("is_orphan_reaction")
        or signal.get("orphan_reaction_count")
    )


def _is_protected_or_continuity_blocked(signal: dict) -> bool:
    role = _story_role(signal)
    if role in {"protected", "continuity_blocked"}:
        return True

    if bool(signal.get("protected") or signal.get("continuity_blocked")):
        return True

    blocking_reasons = signal.get("blocking_reasons") or []
    if isinstance(blocking_reasons, str):
        blocking_reasons = [blocking_reasons]

    normalized = " ".join(str(reason).lower() for reason in blocking_reasons)
    return "protected" in normalized or "continuity" in normalized
