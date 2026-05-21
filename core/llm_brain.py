from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

try:
    import torch  # type: ignore
except Exception:
    class _TorchVersionShim:
        cuda = None

    class _TorchShim:
        version = _TorchVersionShim()

    torch = _TorchShim()  # type: ignore

try:
    from core.llm_shadow_mode import LLM_SHADOW_MODE
except Exception:
    LLM_SHADOW_MODE = True


logger = logging.getLogger(__name__)

MAX_CONTEXT_LENGTH = 32768
DEFAULT_TIMEOUT_SECONDS = 10.0

MODEL_FALLBACK_CHAIN = [
    "qwen3.6-27b:UD-Q4_K_XL",
    "qwen3.6-27b:Q5_K_M",
    "qwen3.6-35b-a3b:Q4_K_XL",
    "qwen3-32b:Q4_K_M",
    "qwen3.6-14b:Q8",
]


@dataclass
class LLMBrainDecision:
    decision_type: str
    recommended_index: int | None
    recommended_order: list[int] | None
    reasoning: str
    confidence: float
    model_used: str
    shadow_mode: bool = True
    warnings: list[str] = field(default_factory=list)
    raw_response: dict | None = None


class LLMBrain:
    """
    LLM-Entscheidungsmodul für Zenith Phase 3.
    Läuft im LLM_SHADOW-Mode: trifft Entscheidungen, überschreibt noch nichts.
    Kommuniziert mit llama-server via OpenAI-kompatibler REST-API.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        model: str = "local",
        context_length: int = MAX_CONTEXT_LENGTH,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.context_length = min(int(context_length), MAX_CONTEXT_LENGTH)
        self.timeout_seconds = min(float(timeout_seconds), DEFAULT_TIMEOUT_SECONDS)

    def is_available(self) -> bool:
        """Prüft ob llama-server erreichbar ist. Niemals crashen wenn nicht."""
        try:
            request = urllib.request.Request(
                self._url("/health"),
                method="GET",
            )
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                return 200 <= int(status) < 500
        except Exception:
            return False

    def decide_hook(
        self,
        candidates: list[dict],
        job_context: dict,
    ) -> LLMBrainDecision:
        """
        Bewertet Hook-Kandidaten und empfiehlt den besten.
        Input: Liste von Kandidaten mit start, end, highlight_score, confidence
        Output: LLMBrainDecision mit recommended_index, reasoning, confidence
        Schema-konform: JSON-Output via Grammar-Constraint erzwingen.
        Im LLM_SHADOW_MODE: Ergebnis loggen, aber Pipeline nicht verändern.
        """
        cuda_warnings = self._cuda_warnings()

        payload = {
            "decision_type": "hook",
            "context_length": self.context_length,
            "job_context": job_context,
            "candidates": candidates,
            "required_json_schema": {
                "recommended_index": "int",
                "reasoning": "string",
                "confidence": "float 0.0-1.0",
            },
        }

        try:
            raw_response = self._chat_completion(
                system_prompt=(
                    "You are Zenith's local LLM Brain. "
                    "Pick the strongest hook candidate for a YouTube edit. "
                    "Return only valid JSON. No markdown. No chain-of-thought."
                ),
                user_payload=payload,
                grammar_kind="hook",
            )
            parsed = self._parse_llm_json(raw_response)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            return self._unavailable_decision(
                decision_type="hook",
                warnings=cuda_warnings,
                raw_error=exc,
            )
        except Exception as exc:
            return self._fallback_decision(
                decision_type="hook",
                candidates_count=len(candidates),
                warnings=[*cuda_warnings, "json_parse_error"],
                raw_response={"error": str(exc)},
            )

        decision = self._build_hook_decision(
            parsed=parsed,
            candidates_count=len(candidates),
            warnings=cuda_warnings,
            raw_response=raw_response,
        )
        self._log_shadow_decision(decision)
        return decision

    def decide_segment_order(
        self,
        segments: list[dict],
        arc_hints: dict | None = None,
    ) -> LLMBrainDecision:
        """
        Schlägt optimale Segment-Reihenfolge vor (setup→conflict→payoff).
        Input: Segmentliste mit story_role, arc_phase, energy_score
        Output: LLMBrainDecision mit recommended_order (list[int]), reasoning
        Im LLM_SHADOW_MODE: Ergebnis loggen, aber Pipeline nicht verändern.
        """
        cuda_warnings = self._cuda_warnings()

        payload = {
            "decision_type": "segment_order",
            "context_length": self.context_length,
            "arc_hints": arc_hints or {},
            "segments": segments,
            "required_json_schema": {
                "recommended_order": "list[int]",
                "reasoning": "string",
                "confidence": "float 0.0-1.0",
            },
        }

        try:
            raw_response = self._chat_completion(
                system_prompt=(
                    "You are Zenith's local LLM Brain. "
                    "Recommend a story order using setup, conflict, and payoff. "
                    "Return only valid JSON. No markdown. No chain-of-thought."
                ),
                user_payload=payload,
                grammar_kind="segment_order",
            )
            parsed = self._parse_llm_json(raw_response)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            return self._unavailable_decision(
                decision_type="segment_order",
                warnings=cuda_warnings,
                raw_error=exc,
            )
        except Exception as exc:
            return self._fallback_decision(
                decision_type="segment_order",
                segments_count=len(segments),
                warnings=[*cuda_warnings, "json_parse_error"],
                raw_response={"error": str(exc)},
            )

        decision = self._build_segment_order_decision(
            parsed=parsed,
            segments_count=len(segments),
            warnings=cuda_warnings,
            raw_response=raw_response,
        )
        self._log_shadow_decision(decision)
        return decision

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _chat_completion(
        self,
        system_prompt: str,
        user_payload: dict[str, Any],
        grammar_kind: str,
    ) -> dict[str, Any]:
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            "temperature": 0.2,
            "top_p": 0.8,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
            "grammar": self._json_grammar(grammar_kind),
            "chat_template_kwargs": {"enable_thinking": False},
            "extra_body": {
                "chat_template_kwargs": {"enable_thinking": False},
            },
        }

        request = urllib.request.Request(
            self._url("/v1/chat/completions"),
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body)

    def _json_grammar(self, grammar_kind: str) -> str:
        if grammar_kind == "segment_order":
            return (
                'root ::= "{" ws "\\"recommended_order\\"" ws ":" ws array ws "," '
                'ws "\\"reasoning\\"" ws ":" ws string ws "," '
                'ws "\\"confidence\\"" ws ":" ws number ws "}"\n'
                'array ::= "[" ws (number (ws "," ws number)*)? ws "]"\n'
                'string ::= "\\"" ([^"\\\\] | "\\\\" .)* "\\""\n'
                'number ::= "-"? [0-9]+ ("." [0-9]+)?\n'
                'ws ::= [ \\t\\n\\r]*'
            )

        return (
            'root ::= "{" ws "\\"recommended_index\\"" ws ":" ws number ws "," '
            'ws "\\"reasoning\\"" ws ":" ws string ws "," '
            'ws "\\"confidence\\"" ws ":" ws number ws "}"\n'
            'string ::= "\\"" ([^"\\\\] | "\\\\" .)* "\\""\n'
            'number ::= "-"? [0-9]+ ("." [0-9]+)?\n'
            'ws ::= [ \\t\\n\\r]*'
        )

    def _parse_llm_json(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        choices = raw_response.get("choices")
        if not choices:
            raise ValueError("missing choices")

        message = choices[0].get("message", {})
        content = message.get("content")

        if isinstance(content, dict):
            return content

        if not isinstance(content, str):
            raise ValueError("message content is not a string")

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("parsed LLM response is not an object")

        return parsed

    def _build_hook_decision(
        self,
        parsed: dict[str, Any],
        candidates_count: int,
        warnings: list[str],
        raw_response: dict[str, Any],
    ) -> LLMBrainDecision:
        local_warnings = list(warnings)

        recommended_index = parsed.get("recommended_index")
        if not isinstance(recommended_index, int):
            local_warnings.append("invalid_recommended_index")
            recommended_index = 0 if candidates_count > 0 else None

        if isinstance(recommended_index, int):
            if recommended_index < 0 or recommended_index >= candidates_count:
                local_warnings.append("invalid_recommended_index")
                recommended_index = 0 if candidates_count > 0 else None

        return LLMBrainDecision(
            decision_type="hook",
            recommended_index=recommended_index,
            recommended_order=None,
            reasoning=str(parsed.get("reasoning", "")),
            confidence=self._clamp_confidence(parsed.get("confidence", 0.0)),
            model_used=str(raw_response.get("model", self.model)),
            shadow_mode=True,
            warnings=local_warnings,
            raw_response=raw_response,
        )

    def _build_segment_order_decision(
        self,
        parsed: dict[str, Any],
        segments_count: int,
        warnings: list[str],
        raw_response: dict[str, Any],
    ) -> LLMBrainDecision:
        local_warnings = list(warnings)

        recommended_order = parsed.get("recommended_order")
        valid_order = (
            isinstance(recommended_order, list)
            and all(isinstance(item, int) for item in recommended_order)
            and sorted(recommended_order) == list(range(segments_count))
        )

        if not valid_order:
            local_warnings.append("invalid_recommended_order")
            recommended_order = list(range(segments_count))

        return LLMBrainDecision(
            decision_type="segment_order",
            recommended_index=None,
            recommended_order=recommended_order,
            reasoning=str(parsed.get("reasoning", "")),
            confidence=self._clamp_confidence(parsed.get("confidence", 0.0)),
            model_used=str(raw_response.get("model", self.model)),
            shadow_mode=True,
            warnings=local_warnings,
            raw_response=raw_response,
        )

    def _unavailable_decision(
        self,
        decision_type: str,
        warnings: list[str],
        raw_error: Exception,
    ) -> LLMBrainDecision:
        local_warnings = [*warnings, "llm_unavailable"]

        decision = LLMBrainDecision(
            decision_type=decision_type,
            recommended_index=0 if decision_type == "hook" else None,
            recommended_order=[] if decision_type == "segment_order" else None,
            reasoning="LLM unavailable; using safe fallback in shadow mode.",
            confidence=0.0,
            model_used=self.model,
            shadow_mode=True,
            warnings=local_warnings,
            raw_response={"error": str(raw_error)},
        )
        self._log_shadow_decision(decision)
        return decision

    def _fallback_decision(
        self,
        decision_type: str,
        candidates_count: int = 0,
        segments_count: int = 0,
        warnings: list[str] | None = None,
        raw_response: dict | None = None,
    ) -> LLMBrainDecision:
        if decision_type == "segment_order":
            recommended_index = None
            recommended_order = list(range(segments_count))
        else:
            recommended_index = 0 if candidates_count > 0 else None
            recommended_order = None

        decision = LLMBrainDecision(
            decision_type=decision_type,
            recommended_index=recommended_index,
            recommended_order=recommended_order,
            reasoning="Fallback due to invalid LLM JSON response.",
            confidence=0.0,
            model_used=self.model,
            shadow_mode=True,
            warnings=list(warnings or []),
            raw_response=raw_response,
        )
        self._log_shadow_decision(decision)
        return decision

    def _cuda_warnings(self) -> list[str]:
        cuda_ver = getattr(getattr(torch, "version", None), "cuda", None)
        if cuda_ver and str(cuda_ver).startswith("13.2"):
            logger.warning(
                "[LLM-BRAIN-CUDA-WARNING] CUDA 13.2 detected. "
                "Qwen 3.6 may produce gibberish output. "
                "Use Unsloth prebuild b8811 or downgrade to CUDA 12.x."
            )
            return ["cuda_13_2_detected"]
        return []

    def _clamp_confidence(self, value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0

        if numeric < 0.0:
            return 0.0
        if numeric > 1.0:
            return 1.0
        return numeric

    def _log_shadow_decision(self, decision: LLMBrainDecision) -> None:
        if LLM_SHADOW_MODE:
            logger.info(
                "[LLM-BRAIN-SHADOW] type=%s confidence=%.3f warnings=%s",
                decision.decision_type,
                decision.confidence,
                decision.warnings,
            )
