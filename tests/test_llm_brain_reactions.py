from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from core.llm_brain import LLMBrain, LLMReactionDecision


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


def _candidates() -> list[dict]:
    return [
        {
            "start": 10.0,
            "end": 11.2,
            "beat_type": "friend_loud_reaction",
            "friend_text": "Was war das denn?",
            "ali_context_text": "Komm mit, komm mit!",
            "evidence": {"trigger": "friend_voice_intensity"},
            "transcript_context": [
                {
                    "start": 8.0,
                    "end": 9.5,
                    "speaker": "ali",
                    "text": "Komm mit, komm mit!",
                },
                {
                    "start": 10.0,
                    "end": 11.2,
                    "speaker": "friend",
                    "text": "Was war das denn?",
                },
            ],
        },
        {
            "start": 22.0,
            "end": 22.4,
            "beat_type": "friend_reaction_keyword",
            "friend_text": "Ja.",
            "ali_context_text": "",
            "evidence": {"keyword": "ja"},
            "transcript_context": [
                {
                    "start": 22.0,
                    "end": 22.4,
                    "speaker": "friend",
                    "text": "Ja.",
                }
            ],
        },
    ]


def test_decide_reactions_parses_json_selection_and_sends_reaction_prompt():
    brain = LLMBrain()
    mocked_response = _mock_llama_response(
        _chat_payload(
            {
                "selections": [
                    {
                        "candidate_index": 0,
                        "is_real_reaction": True,
                        "confidence": 0.82,
                        "reason": "Clear surprised response to Ali's callout.",
                    },
                    {
                        "candidate_index": 1,
                        "is_real_reaction": False,
                        "confidence": 0.15,
                        "reason": "Too generic and not a marked reaction.",
                    },
                ]
            },
            model="qwen3.6-27b:UD-Q4_K_XL",
        )
    )

    with patch("core.llm_brain.urllib.request.urlopen", return_value=mocked_response) as mocked_urlopen:
        decision = brain.decide_reactions(
            candidates=_candidates(),
            job_context={"job_id": "job_test", "channel_type": "gaming_main"},
        )

    request = mocked_urlopen.call_args.args[0]
    body = json.loads(request.data.decode("utf-8"))

    assert isinstance(decision, LLMReactionDecision)
    assert decision.decision_type == "friend_reactions"
    assert decision.model_used == "qwen3.6-27b:UD-Q4_K_XL"
    assert decision.shadow_mode is True
    assert decision.selections[0].candidate_index == 0
    assert decision.selections[0].is_real_reaction is True
    assert decision.selections[0].confidence == 0.82
    assert decision.selections[1].candidate_index == 1
    assert decision.selections[1].is_real_reaction is False
    assert decision.selections[1].confidence == 0.15
    assert "Du bist ein Video-Editor" in body["messages"][0]["content"]
    assert body["response_format"] == {"type": "json_object"}
    assert body["chat_template_kwargs"]["enable_thinking"] is False
    assert body["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False
    assert body["messages"][1]["content"]
    assert body["max_tokens"] == 4096
    assert body["temperature"] == 0.0
    assert body["top_p"] == 1.0
    assert body["top_k"] == 1
    assert body["seed"] == 42


def test_decide_reactions_bad_json_falls_back_to_no_selection():
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
        decision = brain.decide_reactions(
            candidates=_candidates(),
            job_context={"job_id": "job_test", "channel_type": "gaming_main"},
        )

    assert isinstance(decision, LLMReactionDecision)
    assert decision.decision_type == "friend_reactions"
    assert len(decision.selections) == 2
    assert all(selection.is_real_reaction is False for selection in decision.selections)
    assert all(selection.confidence == 0.0 for selection in decision.selections)
    assert all(selection.reason for selection in decision.selections)
    assert "json_parse_error" in decision.warnings
