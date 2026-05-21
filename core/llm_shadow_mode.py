from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from core.llm_brain import LLMBrainDecision


logger = logging.getLogger(__name__)

LLM_SHADOW_MODE = True  # Phase 3: Entscheidungen werden geloggt, nicht angewendet


def apply_if_not_shadow(
    decision: "LLMBrainDecision",
    pipeline_fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """
    Wenn LLM_SHADOW_MODE=True: nur loggen, pipeline_fn NICHT aufrufen.
    Wenn LLM_SHADOW_MODE=False: pipeline_fn mit args/kwargs aufrufen.
    Für spätere Phasen: nur diese eine Zeile umschalten.
    """
    if LLM_SHADOW_MODE:
        logger.info(
            "[LLM-SHADOW-MODE] decision_type=%s confidence=%.3f applied=False",
            getattr(decision, "decision_type", "unknown"),
            float(getattr(decision, "confidence", 0.0)),
        )
        return decision

    logger.info(
        "[LLM-SHADOW-MODE] decision_type=%s confidence=%.3f applied=True",
        getattr(decision, "decision_type", "unknown"),
        float(getattr(decision, "confidence", 0.0)),
    )
    return pipeline_fn(*args, **kwargs)
