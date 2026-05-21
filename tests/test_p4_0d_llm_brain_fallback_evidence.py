from __future__ import annotations

import urllib.error

import pytest

from core.llm_brain import LLMBrain, LLMBrainDecision, MODEL_FALLBACK_CHAIN


def _raise_local_llm_unavailable(*args, **kwargs):
    raise urllib.error.URLError("local_llm_unavailable_for_p4_0d_fallback_evidence")


@pytest.mark.local_llm
def test_p4_0d_llm_brain_fallback_decisions_are_safe(monkeypatch):
    monkeypatch.setattr(
        "core.llm_brain.urllib.request.urlopen",
        _raise_local_llm_unavailable,
    )

    brain = LLMBrain(model=MODEL_FALLBACK_CHAIN[0])

    hook_candidates = [
        {
            "start": 0.0,
            "end": 6.0,
            "highlight_score": 0.72,
            "confidence": 0.70,
            "text": "slow setup",
        },
        {
            "start": 6.0,
            "end": 13.0,
            "highlight_score": 0.94,
            "confidence": 0.91,
            "text": "strong early reaction",
        },
    ]

    hook_decision = brain.decide_hook(
        candidates=hook_candidates,
        job_context={"channel": "gaming_main", "target": "longform"},
    )

    segment_order_decision = brain.decide_segment_order(
        segments=[
            {"story_role": "setup", "arc_phase": "intro", "energy_score": 0.45},
            {"story_role": "conflict", "arc_phase": "middle", "energy_score": 0.82},
            {"story_role": "payoff", "arc_phase": "end", "energy_score": 0.91},
        ],
        arc_hints={"target_arc": "setup-conflict-payoff"},
    )

    assert isinstance(hook_decision, LLMBrainDecision)
    assert hook_decision.decision_type == "hook"
    assert hook_decision.shadow_mode is True
    assert hook_decision.recommended_index == 0
    assert hook_decision.confidence == 0.0
    assert hook_decision.raw_response is not None

    assert isinstance(segment_order_decision, LLMBrainDecision)
    assert segment_order_decision.decision_type == "segment_order"
    assert segment_order_decision.shadow_mode is True
    assert segment_order_decision.recommended_order == []
    assert segment_order_decision.confidence == 0.0
    assert segment_order_decision.raw_response is not None
