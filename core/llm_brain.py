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

from core.power_profile import PowerProfile


logger = logging.getLogger(__name__)

MAX_CONTEXT_LENGTH = 32768
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_TIMEOUT_SECONDS = 60.0
REACTION_TEXT_LIMIT = 320
REACTION_CONTEXT_SEGMENT_LIMIT = 8
REACTION_CHUNK_SIZE = 10
REACTION_DETERMINISTIC_SEED = 42

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


@dataclass
class LLMReactionSelection:
    candidate_index: int
    is_real_reaction: bool
    confidence: float
    reason: str


@dataclass
class LLMReactionDecision:
    decision_type: str
    selections: list[LLMReactionSelection]
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
        self.timeout_seconds = min(float(timeout_seconds), MAX_TIMEOUT_SECONDS)

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
        _job = job_context.get("job") if isinstance(job_context, dict) else None
        _power_profile = getattr(_job, "power_profile", PowerProfile.DEFAULT)
        if isinstance(job_context, dict) and job_context.get("power_profile"):
            _power_profile = job_context.get("power_profile")
        _model_tier = PowerProfile.resolve_model_tier(_power_profile)

        payload = {
            "decision_type": "hook",
            "context_length": self.context_length,
            "job_context": job_context,
            "power_profile_model_tier": _model_tier,
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
        job=None,
    ) -> LLMBrainDecision:
        """
        Schlägt optimale Segment-Reihenfolge vor (setup→conflict→payoff).
        Input: Segmentliste mit story_role, arc_phase, energy_score
        Output: LLMBrainDecision mit recommended_order (list[int]), reasoning
        Im LLM_SHADOW_MODE: Ergebnis loggen, aber Pipeline nicht verändern.
        """
        cuda_warnings = self._cuda_warnings()
        _model_tier = PowerProfile.resolve_model_tier(
            getattr(job, "power_profile", PowerProfile.DEFAULT)
        )

        payload = {
            "decision_type": "segment_order",
            "context_length": self.context_length,
            "arc_hints": arc_hints or {},
            "power_profile_model_tier": _model_tier,
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

    def decide_reactions(
        self,
        candidates: list[dict],
        job_context: dict,
    ) -> LLMReactionDecision:
        """
        Bewertet B2-Freund-Reaktionskandidaten konservativ.
        Input je Kandidat: start/end, Texte, Evidence und Transcript-Kontext.
        Output: LLMReactionDecision mit genau einer Selection je Kandidat.
        Fallback ist immer safe: keine echte Reaktion auswählen.
        """
        if len(candidates) > REACTION_CHUNK_SIZE:
            return self._decide_reaction_chunks(candidates, job_context)

        return self._decide_reactions_once(
            candidates=candidates,
            job_context=job_context,
            candidate_indices=list(range(len(candidates))),
        )

    def _decide_reaction_chunks(
        self,
        candidates: list[dict],
        job_context: dict,
    ) -> LLMReactionDecision:
        selections: list[LLMReactionSelection] = []
        warnings: list[str] = []
        raw_chunks: list[dict | None] = []
        model_used = self.model

        for chunk_start in range(0, len(candidates), REACTION_CHUNK_SIZE):
            chunk = candidates[chunk_start : chunk_start + REACTION_CHUNK_SIZE]
            candidate_indices = list(range(chunk_start, chunk_start + len(chunk)))
            chunk_context = dict(job_context or {})
            chunk_context.update(
                {
                    "reaction_chunk_start": chunk_start,
                    "reaction_chunk_size": len(chunk),
                    "reaction_total_candidates": len(candidates),
                }
            )
            chunk_decision = self._decide_reactions_once(
                candidates=chunk,
                job_context=chunk_context,
                candidate_indices=candidate_indices,
            )
            selections.extend(chunk_decision.selections)
            warnings.extend(chunk_decision.warnings)
            raw_chunks.append(chunk_decision.raw_response)
            if chunk_decision.model_used != self.model:
                model_used = chunk_decision.model_used

        decision = LLMReactionDecision(
            decision_type="friend_reactions",
            selections=sorted(selections, key=lambda selection: selection.candidate_index),
            model_used=model_used,
            shadow_mode=True,
            warnings=list(dict.fromkeys(warnings)),
            raw_response={"chunks": raw_chunks},
        )
        self._log_shadow_decision(decision)
        return decision

    def _decide_reactions_once(
        self,
        candidates: list[dict],
        job_context: dict,
        candidate_indices: list[int],
    ) -> LLMReactionDecision:
        cuda_warnings = self._cuda_warnings()
        payload = {
            "decision_type": "friend_reactions",
            "context_length": self.context_length,
            "job_context": job_context,
            "candidates": self._reaction_candidate_payload(
                candidates,
                candidate_indices=candidate_indices,
            ),
            "required_json_schema": {
                "selections": [
                    {
                        "candidate_index": "int",
                        "is_real_reaction": "bool",
                        "confidence": "float 0.0-1.0",
                        "reason": "string",
                    }
                ]
            },
        }

        try:
            raw_response = self._chat_completion(
                system_prompt=(
                    "Du bist ein Video-Editor und entscheidest, welche "
                    "Freund-Reaktionsmomente wirklich lustig/markant genug sind, "
                    "um auf Gameplay zu schneiden (Facecam weg). Ali-Regel 2026-06-22: "
                    "nahezu jeder starke Freund-Moment zählt, aber streng. Trigger breit "
                    "werten: Hype, Schock, Siegesschrei, witzig, lost und dry zählen. "
                    "Generische Sätze und Nicht-Reaktionen raus. Kein Count-Cap, keine "
                    "Dichte-Begrenzung, nie auf eine Zahl auffüllen und nie genuine "
                    "Momente wegen Dichte droppen. Sei KONSERVATIV: nur klar echte "
                    "Momente, im Zweifel NICHT. Nutze den Gesprächskontext. Gib exakt "
                    "eine Selection für jeden candidate_index zurück, auch wenn "
                    "is_real_reaction false ist. "
                    "Return only valid JSON. No markdown. No chain-of-thought."
                ),
                user_payload=payload,
                grammar_kind="friend_reactions",
                max_tokens=4096,
                temperature=0.0,
                top_p=1.0,
                top_k=1,
                seed=REACTION_DETERMINISTIC_SEED,
            )
            parsed = self._parse_llm_json(raw_response)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            return self._fallback_reaction_decision(
                candidates_count=len(candidates),
                candidate_indices=candidate_indices,
                warnings=[*cuda_warnings, "llm_unavailable"],
                raw_response=self._error_payload(exc),
                reason="LLM unavailable; no reaction selected.",
            )
        except Exception as exc:
            return self._fallback_reaction_decision(
                candidates_count=len(candidates),
                candidate_indices=candidate_indices,
                warnings=[*cuda_warnings, "json_parse_error"],
                raw_response={"error": str(exc)},
                reason="Invalid LLM JSON response; no reaction selected.",
            )

        decision = self._build_reaction_decision(
            parsed=parsed,
            candidates_count=len(candidates),
            candidate_indices=candidate_indices,
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
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.8,
        top_k: int | None = None,
        seed: int | None = None,
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
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
            "response_format": {"type": "json_object"},
            "grammar": self._json_grammar(grammar_kind),
            "chat_template_kwargs": {"enable_thinking": False},
            "extra_body": {
                "chat_template_kwargs": {"enable_thinking": False},
            },
        }
        if top_k is not None:
            body["top_k"] = int(top_k)
        if seed is not None:
            body["seed"] = int(seed)

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
        if grammar_kind == "friend_reactions":
            return (
                'root ::= "{" ws "\\"selections\\"" ws ":" ws selections ws "}"\n'
                'selections ::= "[" ws (selection (ws "," ws selection)*)? ws "]"\n'
                'selection ::= "{" ws "\\"candidate_index\\"" ws ":" ws integer ws "," '
                'ws "\\"is_real_reaction\\"" ws ":" ws boolean ws "," '
                'ws "\\"confidence\\"" ws ":" ws number ws "," '
                'ws "\\"reason\\"" ws ":" ws string ws "}"\n'
                'boolean ::= "true" | "false"\n'
                'string ::= "\\"" ([^"\\\\] | "\\\\" .)* "\\""\n'
                'integer ::= "-"? [0-9]+\n'
                'number ::= "-"? [0-9]+ ("." [0-9]+)?\n'
                'ws ::= [ \\t\\n\\r]*'
            )

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

    def _reaction_candidate_payload(
        self,
        candidates: list[dict],
        candidate_indices: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                candidate = {}
            candidate_index = (
                candidate_indices[index]
                if candidate_indices is not None and index < len(candidate_indices)
                else index
            )
            payload.append(
                {
                    "candidate_index": candidate_index,
                    "start": candidate.get("start"),
                    "end": candidate.get("end"),
                    "beat_type": candidate.get("beat_type"),
                    "friend_text": self._clip_reaction_text(
                        candidate.get("friend_text", "")
                    ),
                    "ali_context_text": self._clip_reaction_text(
                        candidate.get("ali_context_text", "")
                    ),
                    "evidence": self._reaction_evidence_payload(
                        candidate.get("evidence", {})
                    ),
                    "transcript_context": self._reaction_context_payload(
                        candidate.get("transcript_context", [])
                    ),
                }
            )
        return payload

    def _clip_reaction_text(self, value: Any) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= REACTION_TEXT_LIMIT:
            return text
        return f"{text[:REACTION_TEXT_LIMIT].rstrip()}..."

    def _reaction_evidence_payload(self, evidence: Any) -> dict[str, Any]:
        if not isinstance(evidence, dict):
            return {}
        compact: dict[str, Any] = {}
        for key in (
            "pattern",
            "trigger",
            "keyword",
            "gap_seconds",
            "max_friend_intensity",
            "friend_loud_rms_dbfs_threshold",
        ):
            if key in evidence:
                compact[key] = evidence[key]
        return compact

    def _reaction_context_payload(self, transcript_context: Any) -> list[dict[str, Any]]:
        if not isinstance(transcript_context, list):
            return []
        context = []
        for raw_segment in transcript_context[:REACTION_CONTEXT_SEGMENT_LIMIT]:
            if not isinstance(raw_segment, dict):
                continue
            context.append(
                {
                    "start": raw_segment.get("start"),
                    "end": raw_segment.get("end"),
                    "speaker": raw_segment.get("speaker"),
                    "text": self._clip_reaction_text(raw_segment.get("text", "")),
                }
            )
        return context

    def _build_reaction_decision(
        self,
        parsed: dict[str, Any],
        candidates_count: int,
        candidate_indices: list[int] | None,
        warnings: list[str],
        raw_response: dict[str, Any],
    ) -> LLMReactionDecision:
        expected_indices = (
            list(candidate_indices)
            if candidate_indices is not None
            else list(range(candidates_count))
        )
        expected_index_set = set(expected_indices)
        raw_selections = parsed.get("selections")
        if not isinstance(raw_selections, list):
            return self._fallback_reaction_decision(
                candidates_count=candidates_count,
                candidate_indices=expected_indices,
                warnings=[*warnings, "invalid_reaction_selections"],
                raw_response=raw_response,
                reason="LLM response missing selections; no reaction selected.",
            )

        local_warnings = list(warnings)
        selections_by_index: dict[int, LLMReactionSelection] = {}
        for raw_selection in raw_selections:
            if not isinstance(raw_selection, dict):
                local_warnings.append("invalid_reaction_selection_item")
                continue
            candidate_index = raw_selection.get("candidate_index")
            if not isinstance(candidate_index, int):
                local_warnings.append("invalid_reaction_candidate_index")
                continue
            if candidate_index not in expected_index_set:
                local_warnings.append("invalid_reaction_candidate_index")
                continue

            selections_by_index[candidate_index] = LLMReactionSelection(
                candidate_index=candidate_index,
                is_real_reaction=bool(raw_selection.get("is_real_reaction", False)),
                confidence=self._clamp_confidence(raw_selection.get("confidence", 0.0)),
                reason=str(raw_selection.get("reason", "")),
            )

        selections = []
        for index in expected_indices:
            selection = selections_by_index.get(index)
            if selection is None:
                local_warnings.append("missing_reaction_selection")
                selection = LLMReactionSelection(
                    candidate_index=index,
                    is_real_reaction=False,
                    confidence=0.0,
                    reason="Missing LLM verdict; no reaction selected.",
                )
            selections.append(selection)

        return LLMReactionDecision(
            decision_type="friend_reactions",
            selections=selections,
            model_used=str(raw_response.get("model", self.model)),
            shadow_mode=True,
            warnings=local_warnings,
            raw_response=raw_response,
        )

    def _fallback_reaction_decision(
        self,
        candidates_count: int,
        candidate_indices: list[int] | None = None,
        warnings: list[str] | None = None,
        raw_response: dict | None = None,
        reason: str = "Safe fallback; no reaction selected.",
    ) -> LLMReactionDecision:
        expected_indices = (
            list(candidate_indices)
            if candidate_indices is not None
            else list(range(candidates_count))
        )
        decision = LLMReactionDecision(
            decision_type="friend_reactions",
            selections=[
                LLMReactionSelection(
                    candidate_index=index,
                    is_real_reaction=False,
                    confidence=0.0,
                    reason=reason,
                )
                for index in expected_indices
            ],
            model_used=self.model,
            shadow_mode=True,
            warnings=list(warnings or []),
            raw_response=raw_response,
        )
        self._log_shadow_decision(decision)
        return decision

    def _error_payload(self, exc: Exception) -> dict[str, Any]:
        payload = {"error": str(exc)}
        if isinstance(exc, urllib.error.HTTPError):
            try:
                payload["response_body"] = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                pass
        return payload

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
            confidence = getattr(decision, "confidence", None)
            if confidence is None and hasattr(decision, "selections"):
                selections = getattr(decision, "selections", [])
                confidence_values = [
                    selection.confidence
                    for selection in selections
                    if getattr(selection, "is_real_reaction", False)
                ]
                confidence = max(confidence_values, default=0.0)
            logger.info(
                "[LLM-BRAIN-SHADOW] type=%s confidence=%.3f warnings=%s",
                decision.decision_type,
                confidence,
                decision.warnings,
            )
