from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from core.llm_brain import LLMBrain, LLMBrainDecision
from core.shorts_highlight_extractor import LLM_DISABLED, LLM_SHADOW
from core.timeline_signal_consumer import (
    SIGNAL_DYNAMIC_PACING,
    SIGNAL_EMOTIONAL_ARC,
    SIGNAL_HOOK_IDENTIFICATION,
    SIGNAL_REACTION_SHOT,
    TimelineSignalConsumer,
)
from models.edit_timeline import EditTimeline
from models.shorts_clip import ShortsClip
from models.shorts_reframe_plan import ShortsReframePlan

logger = logging.getLogger(__name__)

LAYOUT_GAMEPLAY_CENTERED = "gameplay_centered"
LAYOUT_FACECAM_CENTERED = "facecam_centered"
LAYOUT_HYBRID_SPLIT = "hybrid_split"

PLATFORM_YOUTUBE_SHORTS = "youtube_shorts"

DOMINANCE_THRESHOLD = 0.6

SAFE_ZONE_TOP_PX = 120
SAFE_ZONE_BOTTOM_PX = 120

GAMEPLAY_CENTERED_FILTER = "crop=1080:1920:420:0"
GAMEPLAY_CENTERED_ZOOMPAN_FILTER = (
    "crop=1080:1920:420:0,"
    "zoompan=z='1':x='iw/2-(iw/zoom/2)':y=0:d=1:s=1080x1920"
)
STACK_60_40_FILTER = (
    "[0:v]crop=1080:1152:420:0[top];"
    "[0:v]crop=1080:768:420:312[bottom];"
    "[top][bottom]vstack"
)

HYBRID_RATIONALE_TAG = "hybrid"

PROMPT_TEMPLATE = (
    "Du bist ein YouTube-Shorts-Experte. Welches Layout passt am besten zu diesem "
    "Gaming-Highlight? Waehle: gameplay_centered, facecam_centered oder hybrid_split. "
    "Begruende in einem Satz. Signalwerte: {signals_json}"
)


@dataclass(frozen=True)
class _LayoutSignalSummary:
    hook: float
    pacing: float
    reaction: float
    arc: float
    has_signal_data: bool
    action_movement_detected: bool

    def to_dict(self) -> dict[str, float | bool]:
        return {
            "hook": self.hook,
            "pacing": self.pacing,
            "reaction": self.reaction,
            "arc": self.arc,
            "has_signal_data": self.has_signal_data,
            "action_movement_detected": self.action_movement_detected,
        }


class ShortsReframePlanner:
    def __init__(
        self,
        signal_consumer: TimelineSignalConsumer | None = None,
        llm_brain: LLMBrain | None = None,
    ) -> None:
        self.signal_consumer = signal_consumer or TimelineSignalConsumer()
        self.llm_brain = llm_brain or LLMBrain()

    def plan_reframe(
        self,
        clip: ShortsClip,
        timeline: EditTimeline,
        llm_mode: str = LLM_SHADOW,
    ) -> ShortsReframePlan:
        summary = self._signal_summary_for_clip(clip)
        layout_type, rationale = self._choose_layout(summary)

        normalized_mode = str(llm_mode or LLM_SHADOW).strip().upper()
        if normalized_mode == LLM_SHADOW:
            llm_note = self._llm_shadow_note(summary)
            if llm_note:
                rationale = f"{rationale} LLM_SHADOW: {llm_note}"
        elif normalized_mode != LLM_DISABLED:
            logger.info(
                "[shorts_reframe_planner] unknown_llm_mode=%s using heuristic layout",
                llm_mode,
            )

        return ShortsReframePlan(
            layout_type=layout_type,
            ffmpeg_crop_filter=self._filter_for_layout(layout_type, summary),
            target_aspect_ratio="9:16",
            safe_zone_top_px=SAFE_ZONE_TOP_PX,
            safe_zone_bottom_px=SAFE_ZONE_BOTTOM_PX,
            face_tracking_enabled=False,
            layout_rationale=rationale,
            platform_preset=PLATFORM_YOUTUBE_SHORTS,
        )

    def _signal_summary_for_clip(self, clip: ShortsClip) -> _LayoutSignalSummary:
        start = float(getattr(clip, "source_start_time", 0.0) or 0.0)
        end = float(getattr(clip, "source_end_time", start) or start)

        hook = self._safe_best_score(start, end, SIGNAL_HOOK_IDENTIFICATION)
        pacing = self._safe_best_score(start, end, SIGNAL_DYNAMIC_PACING)
        reaction = self._safe_best_score(start, end, SIGNAL_REACTION_SHOT)
        arc = self._safe_best_score(start, end, SIGNAL_EMOTIONAL_ARC)

        has_signal_data = self._has_any_signal_data(
            start,
            end,
            (
                SIGNAL_HOOK_IDENTIFICATION,
                SIGNAL_DYNAMIC_PACING,
                SIGNAL_REACTION_SHOT,
                SIGNAL_EMOTIONAL_ARC,
            ),
        )
        action_movement_detected = self._action_movement_detected(start, end)

        return _LayoutSignalSummary(
            hook=hook,
            pacing=pacing,
            reaction=reaction,
            arc=arc,
            has_signal_data=has_signal_data,
            action_movement_detected=action_movement_detected,
        )

    def _safe_best_score(self, start: float, end: float, signal_name: str) -> float:
        try:
            value = self.signal_consumer.best_score_for_segment(start, end, signal_name)
            return max(0.0, min(1.0, float(value or 0.0)))
        except Exception:
            return 0.0

    def _has_any_signal_data(
        self,
        start: float,
        end: float,
        signal_names: tuple[str, ...],
    ) -> bool:
        for signal_name in signal_names:
            try:
                if self.signal_consumer.signals_for_segment(start, end, signal_name):
                    return True
            except Exception:
                continue
        return False

    def _action_movement_detected(self, start: float, end: float) -> bool:
        signal_names = (
            SIGNAL_DYNAMIC_PACING,
            SIGNAL_HOOK_IDENTIFICATION,
            SIGNAL_REACTION_SHOT,
        )
        for signal_name in signal_names:
            try:
                signals = self.signal_consumer.signals_for_segment(start, end, signal_name)
            except Exception:
                signals = []

            for signal in signals:
                if not isinstance(signal, dict):
                    continue
                if bool(signal.get("action_movement_detected")):
                    return True
                metadata = signal.get("metadata")
                if isinstance(metadata, dict) and bool(metadata.get("action_movement_detected")):
                    return True

        return False

    def _choose_layout(
        self,
        summary: _LayoutSignalSummary,
    ) -> tuple[str, str]:
        if not summary.has_signal_data or max(
            summary.hook,
            summary.pacing,
            summary.reaction,
            summary.arc,
        ) <= 0.0:
            return (
                LAYOUT_HYBRID_SPLIT,
                "No usable 2B-PRO signal data found; hybrid_split is the safe default.",
            )

        hook_and_pacing_dominate = (
            summary.hook > DOMINANCE_THRESHOLD
            and summary.pacing > DOMINANCE_THRESHOLD
            and (summary.hook + summary.pacing) >= (summary.reaction + summary.arc)
        )
        if hook_and_pacing_dominate:
            return (
                LAYOUT_GAMEPLAY_CENTERED,
                (
                    "Hook and dynamic pacing dominate; gameplay_centered keeps the "
                    "gameplay action central."
                ),
            )

        reaction_and_arc_dominate = (
            summary.reaction > DOMINANCE_THRESHOLD
            and summary.arc > DOMINANCE_THRESHOLD
            and (summary.reaction + summary.arc) > (summary.hook + summary.pacing)
        )
        if reaction_and_arc_dominate:
            return (
                LAYOUT_FACECAM_CENTERED,
                (
                    "Reaction and emotional arc dominate; facecam_centered prioritizes "
                    "creator expression."
                ),
            )

        return (
            LAYOUT_HYBRID_SPLIT,
            (
                "hybrid: gameplay dominant oben, facecam unten; no single signal group "
                "clearly dominates."
            ),
        )

    def _filter_for_layout(
        self,
        layout_type: str,
        summary: _LayoutSignalSummary,
    ) -> str:
        if layout_type == LAYOUT_GAMEPLAY_CENTERED:
            if summary.action_movement_detected:
                return GAMEPLAY_CENTERED_ZOOMPAN_FILTER
            return GAMEPLAY_CENTERED_FILTER

        if layout_type == LAYOUT_FACECAM_CENTERED:
            return STACK_60_40_FILTER

        return STACK_60_40_FILTER

    def _llm_shadow_note(self, summary: _LayoutSignalSummary) -> str:
        signals_json = json.dumps(summary.to_dict(), ensure_ascii=False)
        prompt = PROMPT_TEMPLATE.format(signals_json=signals_json)

        try:
            decision = self.llm_brain.decide_hook(
                candidates=[
                    {
                        "layout_type": LAYOUT_GAMEPLAY_CENTERED,
                        "signals": summary.to_dict(),
                    },
                    {
                        "layout_type": LAYOUT_FACECAM_CENTERED,
                        "signals": summary.to_dict(),
                    },
                    {
                        "layout_type": LAYOUT_HYBRID_SPLIT,
                        "signals": summary.to_dict(),
                    },
                ],
                job_context={
                    "prompt": prompt,
                    "signals_json": signals_json,
                    "task": "shorts_reframe_layout_shadow",
                },
            )
        except Exception as exc:
            logger.info("[shorts_reframe_planner] LLM_SHADOW failed=%s", exc)
            return ""

        logger.info("[shorts_reframe_planner] LLM_SHADOW response=%s", decision)
        return self._decision_note(decision)

    def _decision_note(self, decision: LLMBrainDecision) -> str:
        reasoning = str(getattr(decision, "reasoning", "") or "").strip()
        recommended_index = getattr(decision, "recommended_index", None)
        layout_names = [
            LAYOUT_GAMEPLAY_CENTERED,
            LAYOUT_FACECAM_CENTERED,
            LAYOUT_HYBRID_SPLIT,
        ]

        if isinstance(recommended_index, int) and 0 <= recommended_index < len(layout_names):
            recommended_layout = layout_names[recommended_index]
            if reasoning:
                return f"recommended={recommended_layout}; {reasoning}"
            return f"recommended={recommended_layout}"

        return reasoning
