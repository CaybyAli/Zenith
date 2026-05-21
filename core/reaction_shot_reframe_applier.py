"""
P3-3E: Reaction Shot Placement -> ReframePlan applier.

Liest reaction_shot_placement-Signale aus dem Job und fuegt Layout-Switch-
Instruktionen in den ReframePlan ein. Bestehende Instruktionen werden nicht
geloescht, nur ergaenzt.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from core.timeline_signal_consumer import (
    SIGNAL_REACTION_SHOT,
    TimelineSignalConsumer,
)
from models.framing_instruction import FramingInstruction

logger = logging.getLogger(__name__)

_MIN_PLACEMENT_SCORE = 0.3


def apply_reaction_shots_to_reframe_plan(
    reframe_plan: Any,
    job: Any,
) -> Any:
    """
    Ergaenzt reframe_plan.instructions mit Reaction-Shot-Layout-Switches.

    - Liest reaction_shot_placement-Signale aus job.
    - Pro Signal mit can_insert_clip=True, can_move_clip=True oder can_auto_place=True
      und placement_score >= 0.3 wird eine facecam_emphasis-Instruktion angehaengt.
    - Bestehende Instruktionen bleiben erhalten.
    - Kein Crash wenn Signal, Plan oder Felder fehlen.
    - Gibt den moeglicherweise modifizierten reframe_plan zurueck.
    """
    if reframe_plan is None or job is None:
        return reframe_plan

    try:
        consumer = TimelineSignalConsumer.from_job(job)
        bundle = consumer.read(SIGNAL_REACTION_SHOT)

        if not bundle.available:
            logger.debug("[P3-3E-REACTION] no reaction shot signals available")
            return reframe_plan

        added_count = 0
        for signal in bundle.signals:
            instruction = _instruction_from_signal(reframe_plan, job, signal)
            if instruction is None:
                continue

            if _append_instruction(reframe_plan, instruction):
                added_count += 1

        logger.debug(
            "[P3-3E-REACTION] added %d reaction shot layout switches to reframe plan",
            added_count,
        )
    except Exception as exc:
        logger.warning("[P3-3E-REACTION] apply failed, plan unchanged: %s", exc)

    return reframe_plan


def _instruction_from_signal(
    reframe_plan: Any,
    job: Any,
    signal: dict,
) -> FramingInstruction | dict | None:
    try:
        can_insert = bool(
            signal.get("can_insert_clip")
            or signal.get("can_move_clip")
            or signal.get("can_auto_place")
        )
        placement_score = float(signal.get("placement_score") or 0.0)
    except Exception:
        return None

    if not can_insert or placement_score < _MIN_PLACEMENT_SCORE:
        return None

    position = _safe_float(
        signal.get("suggested_position")
        or signal.get("start_seconds")
        or signal.get("timestamp")
        or 0.0
    )
    segment_id = str(
        signal.get("trigger_segment_id")
        or signal.get("source_segment_id")
        or signal.get("segment_id")
        or f"reaction_shot_at_{position:.3f}"
    )

    metadata = {
        "type": "layout_switch",
        "at_seconds": position,
        "layout": "facecam_emphasis",
        "source": "reaction_shot_placement",
        "placement_score": placement_score,
    }

    if _looks_like_real_reframe_plan(reframe_plan):
        return FramingInstruction(
            instruction_id=f"reaction_layout_{uuid.uuid4().hex[:12]}",
            job_id=str(getattr(reframe_plan, "job_id", getattr(job, "job_id", "unknown"))),
            timeline_id=str(getattr(reframe_plan, "timeline_id", "unknown")),
            segment_id=segment_id,
            focus_kind="facecam_emphasis",
            layout_kind="facecam_emphasis",
            source_aspect_ratio=str(getattr(reframe_plan, "source_aspect_ratio", "unknown")),
            target_aspect_ratio=str(
                getattr(reframe_plan, "primary_target_aspect_ratio", "unknown")
            ),
            crop_window={},
            notes=["reaction_shot_layout_switch"],
            metadata=metadata,
        )

    return {
        "type": "layout_switch",
        "at_seconds": position,
        "layout": "facecam_emphasis",
        "focus_kind": "facecam_emphasis",
        "layout_kind": "facecam_emphasis",
        "segment_id": segment_id,
        "source": "reaction_shot_placement",
        "placement_score": placement_score,
        "metadata": metadata,
    }


def _append_instruction(reframe_plan: Any, instruction: FramingInstruction | dict) -> bool:
    try:
        if hasattr(reframe_plan, "instructions"):
            if reframe_plan.instructions is None:
                reframe_plan.instructions = []
            reframe_plan.instructions.append(instruction)
            if hasattr(reframe_plan, "plan_notes"):
                reframe_plan.plan_notes.append("Reaction shot layout switch added")
            if hasattr(reframe_plan, "touch"):
                reframe_plan.touch()
            return True

        if isinstance(reframe_plan, dict):
            if reframe_plan.get("instructions") is None:
                reframe_plan["instructions"] = []
            reframe_plan["instructions"].append(instruction)
            notes = reframe_plan.setdefault("plan_notes", [])
            if isinstance(notes, list):
                notes.append("Reaction shot layout switch added")
            return True
    except Exception as exc:
        logger.debug("[P3-3E-REACTION] skipped append due to error: %s", exc)

    return False


def _looks_like_real_reframe_plan(reframe_plan: Any) -> bool:
    return (
        hasattr(reframe_plan, "plan_id")
        and hasattr(reframe_plan, "job_id")
        and hasattr(reframe_plan, "timeline_id")
        and hasattr(reframe_plan, "source_aspect_ratio")
        and hasattr(reframe_plan, "primary_target_aspect_ratio")
    )


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0
