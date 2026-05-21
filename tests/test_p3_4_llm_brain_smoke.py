from __future__ import annotations

import json
import urllib.error
from unittest.mock import MagicMock, patch

from core.llm_brain import LLMBrain, LLMBrainDecision
from core.llm_shadow_mode import apply_if_not_shadow


def _mock_llama_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps(payload).encode("utf-8")

    context = MagicMock()
    context.__enter__.return_value = response
    context.__exit__.return_value = None
    return context


def _chat_payload(content: dict, model: str = "local") -> dict:
    return {
        "model": model,
        "choices": [
            {
                "message": {
                    "content": json.dumps(content),
                }
            }
        ],
    }


def test_llm_brain_unavailable_does_not_crash():
    """llama-server nicht erreichbar -> kein Crash, LLMBrainDecision mit warning."""
    brain = LLMBrain()

    with patch(
        "core.llm_brain.urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        decision = brain.decide_hook(
            candidates=[
                {
                    "start": 0.0,
                    "end": 8.0,
                    "highlight_score": 0.91,
                    "confidence": 0.8,
                }
            ],
            job_context={"channel": "gaming_main"},
        )

    assert isinstance(decision, LLMBrainDecision)
    assert decision.decision_type == "hook"
    assert decision.shadow_mode is True
    assert decision.confidence == 0.0
    assert "llm_unavailable" in decision.warnings


def test_decide_hook_returns_valid_decision_structure():
    """Mock-Response -> LLMBrainDecision vollständig befüllt."""
    brain = LLMBrain()

    mocked_response = _mock_llama_response(
        _chat_payload(
            {
                "recommended_index": 1,
                "reasoning": "Candidate 1 has the strongest early hook.",
                "confidence": 0.86,
            },
            model="qwen3.6-27b:UD-Q4_K_XL",
        )
    )

    with patch("core.llm_brain.urllib.request.urlopen", return_value=mocked_response):
        decision = brain.decide_hook(
            candidates=[
                {
                    "start": 0.0,
                    "end": 6.0,
                    "highlight_score": 0.71,
                    "confidence": 0.7,
                },
                {
                    "start": 6.0,
                    "end": 13.0,
                    "highlight_score": 0.94,
                    "confidence": 0.91,
                },
            ],
            job_context={"channel": "gaming_main", "target": "longform"},
        )

    assert isinstance(decision, LLMBrainDecision)
    assert decision.decision_type == "hook"
    assert decision.recommended_index == 1
    assert decision.recommended_order is None
    assert decision.reasoning
    assert decision.confidence == 0.86
    assert decision.model_used == "qwen3.6-27b:UD-Q4_K_XL"
    assert decision.shadow_mode is True
    assert decision.raw_response is not None


def test_decide_hook_sends_enable_thinking_false_in_api_call():
    """Jeder API-Call muss enable_thinking=False setzen."""
    brain = LLMBrain()

    mocked_response = _mock_llama_response(
        _chat_payload(
            {
                "recommended_index": 0,
                "reasoning": "First candidate is safest.",
                "confidence": 0.8,
            }
        )
    )

    with patch("core.llm_brain.urllib.request.urlopen", return_value=mocked_response) as mocked_urlopen:
        brain.decide_hook(
            candidates=[
                {
                    "start": 0.0,
                    "end": 7.0,
                    "highlight_score": 0.88,
                    "confidence": 0.82,
                }
            ],
            job_context={"channel": "gaming_main"},
        )

    request = mocked_urlopen.call_args.args[0]
    body = json.loads(request.data.decode("utf-8"))

    assert body["chat_template_kwargs"]["enable_thinking"] is False
    assert body["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False


def test_decide_segment_order_returns_valid_decision_structure():
    """Mock-Response -> LLMBrainDecision mit recommended_order."""
    brain = LLMBrain()

    mocked_response = _mock_llama_response(
        _chat_payload(
            {
                "recommended_order": [1, 0, 2],
                "reasoning": "Conflict works better before setup recap and payoff.",
                "confidence": 0.79,
            },
            model="qwen3.6-27b:UD-Q4_K_XL",
        )
    )

    with patch("core.llm_brain.urllib.request.urlopen", return_value=mocked_response):
        decision = brain.decide_segment_order(
            segments=[
                {"story_role": "setup", "arc_phase": "intro", "energy_score": 0.45},
                {"story_role": "conflict", "arc_phase": "middle", "energy_score": 0.82},
                {"story_role": "payoff", "arc_phase": "end", "energy_score": 0.91},
            ],
            arc_hints={"target_arc": "setup-conflict-payoff"},
        )

    assert isinstance(decision, LLMBrainDecision)
    assert decision.decision_type == "segment_order"
    assert decision.recommended_index is None
    assert decision.recommended_order == [1, 0, 2]
    assert decision.reasoning
    assert decision.confidence == 0.79
    assert decision.model_used == "qwen3.6-27b:UD-Q4_K_XL"
    assert decision.shadow_mode is True
    assert decision.raw_response is not None


def test_shadow_mode_does_not_call_pipeline():
    """LLM_SHADOW_MODE=True -> pipeline_fn wird NICHT aufgerufen."""
    decision = LLMBrainDecision(
        decision_type="hook",
        recommended_index=0,
        recommended_order=None,
        reasoning="Shadow mode should not mutate pipeline.",
        confidence=0.9,
        model_used="local",
    )
    pipeline_fn = MagicMock(return_value="pipeline_result")

    result = apply_if_not_shadow(decision, pipeline_fn, "arg1", key="value")

    assert result is decision
    pipeline_fn.assert_not_called()


def test_cuda_warning_logged_on_13_2(caplog):
    """CUDA 13.2 detektiert -> Warning in logs, kein Crash."""
    brain = LLMBrain()

    mocked_response = _mock_llama_response(
        _chat_payload(
            {
                "recommended_index": 0,
                "reasoning": "Valid response despite CUDA warning.",
                "confidence": 0.75,
            }
        )
    )

    with patch("core.llm_brain.torch.version.cuda", "13.2"):
        with patch("core.llm_brain.urllib.request.urlopen", return_value=mocked_response):
            decision = brain.decide_hook(
                candidates=[
                    {
                        "start": 0.0,
                        "end": 5.0,
                        "highlight_score": 0.8,
                        "confidence": 0.7,
                    }
                ],
                job_context={"channel": "gaming_main"},
            )

    assert decision.shadow_mode is True
    assert "cuda_13_2_detected" in decision.warnings
    assert "[LLM-BRAIN-CUDA-WARNING] CUDA 13.2 detected." in caplog.text


def test_json_parse_error_returns_fallback_decision():
    """Kaputte LLM-Antwort -> fallback Index 0, warning='json_parse_error'."""
    brain = LLMBrain()

    mocked_response = _mock_llama_response(
        {
            "model": "local",
            "choices": [
                {
                    "message": {
                        "content": "not valid json",
                    }
                }
            ],
        }
    )

    with patch("core.llm_brain.urllib.request.urlopen", return_value=mocked_response):
        decision = brain.decide_hook(
            candidates=[
                {
                    "start": 0.0,
                    "end": 5.0,
                    "highlight_score": 0.8,
                    "confidence": 0.7,
                },
                {
                    "start": 5.0,
                    "end": 10.0,
                    "highlight_score": 0.6,
                    "confidence": 0.5,
                },
            ],
            job_context={"channel": "gaming_main"},
        )

    assert isinstance(decision, LLMBrainDecision)
    assert decision.decision_type == "hook"
    assert decision.recommended_index == 0
    assert decision.recommended_order is None
    assert decision.confidence == 0.0
    assert decision.shadow_mode is True
    assert "json_parse_error" in decision.warnings

def test_model_capability_resolver_does_not_crash():
    from core.model_capability_resolver import ModelCapabilityResolver

    resolver = ModelCapabilityResolver.detect()

    assert isinstance(resolver.selected_model, str)
    assert len(resolver.selected_model) > 0
    assert isinstance(resolver.reason, str)

    d = resolver.to_dict()
    assert "selected_model" in d
    assert "vram_gb" in d
    assert "ram_gb" in d

