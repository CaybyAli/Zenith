from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any


_ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost"}


class QwenSideTrackError(RuntimeError):
    """Raised when the local Qwen side-track cannot produce a safe result."""


@dataclass(frozen=True)
class QwenSideTrackResult:
    status: str
    role: str
    can_cut: bool
    confidence: float
    notes: list[str] = field(default_factory=list)
    raw_text: str = ""


class LocalQwenSideTrack:
    def __init__(
        self,
        model: str = "qwen3.6:latest",
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.model = self._validate_model(model)
        self.base_url = self._validate_base_url(base_url)
        self.timeout_seconds = self._validate_timeout(timeout_seconds)

    def analyze_json_only(self, prompt: str) -> QwenSideTrackResult:
        if not isinstance(prompt, str) or not prompt.strip():
            raise QwenSideTrackError("prompt must be a non-empty string")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False,
            "options": {
                "temperature": 0,
                "num_predict": 256,
            },
        }

        request = urllib.request.Request(
            self._api_generate_url(),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise QwenSideTrackError(f"ollama http error: {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise QwenSideTrackError(f"ollama local request failed: {exc}") from exc

        try:
            envelope = json.loads(response_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise QwenSideTrackError("ollama response envelope is not valid JSON") from exc

        if not isinstance(envelope, dict):
            raise QwenSideTrackError("ollama response envelope must be a JSON object")

        raw_text = envelope.get("response")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise QwenSideTrackError("ollama response field must be a non-empty string")

        try:
            model_payload = json.loads(raw_text.strip())
        except json.JSONDecodeError as exc:
            raise QwenSideTrackError("qwen model text is not valid JSON") from exc

        if not isinstance(model_payload, dict):
            raise QwenSideTrackError("qwen model JSON must be an object")

        return self._build_result(model_payload, raw_text=raw_text)

    @staticmethod
    def _validate_model(model: str) -> str:
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model must be a non-empty string")
        return model.strip()

    @staticmethod
    def _validate_timeout(timeout_seconds: float) -> float:
        try:
            value = float(timeout_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("timeout_seconds must be numeric") from exc

        if value <= 0:
            raise ValueError("timeout_seconds must be positive")
        return value

    @staticmethod
    def _validate_base_url(base_url: str) -> str:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("base_url must be a non-empty string")

        cleaned = base_url.strip().rstrip("/")
        parsed = urllib.parse.urlparse(cleaned)

        if parsed.scheme != "http":
            raise ValueError("base_url must use local http only")

        host = (parsed.hostname or "").lower()
        if host not in _ALLOWED_LOCAL_HOSTS:
            raise ValueError("base_url must point to localhost or 127.0.0.1")

        if parsed.username or parsed.password:
            raise ValueError("base_url must not contain credentials")

        if parsed.path not in ("", "/"):
            raise ValueError("base_url must not contain a path")

        return cleaned

    def _api_generate_url(self) -> str:
        return f"{self.base_url}/api/generate"

    def _build_result(
        self,
        payload: dict[str, Any],
        raw_text: str,
    ) -> QwenSideTrackResult:
        required = {"status", "role", "can_cut", "confidence", "notes"}
        missing = sorted(required - set(payload))
        if missing:
            raise QwenSideTrackError(f"missing qwen fields: {', '.join(missing)}")

        status = payload.get("status")
        if status != "ok":
            raise QwenSideTrackError("status must be exactly 'ok'")

        role = payload.get("role")
        if role != "analysis_only":
            raise QwenSideTrackError("role must be exactly 'analysis_only'")

        can_cut = payload.get("can_cut")
        if type(can_cut) is not bool or can_cut is not False:
            raise QwenSideTrackError("can_cut must be exactly false")

        confidence_value = payload.get("confidence")
        if isinstance(confidence_value, bool) or not isinstance(confidence_value, (int, float)):
            raise QwenSideTrackError("confidence must be a number")

        confidence = float(confidence_value)
        if confidence < 0.0 or confidence > 1.0:
            raise QwenSideTrackError("confidence must be between 0.0 and 1.0")

        notes = payload.get("notes")
        if not isinstance(notes, list) or not all(isinstance(item, str) for item in notes):
            raise QwenSideTrackError("notes must be a list of strings")

        return QwenSideTrackResult(
            status=status,
            role=role,
            can_cut=can_cut,
            confidence=confidence,
            notes=list(notes),
            raw_text=raw_text,
        )
