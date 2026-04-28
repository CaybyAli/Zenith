from __future__ import annotations

from models.jarvis_response import JarvisResponse
from shared.jarvis_enums import JarvisCommandType


class JarvisResponseBuilder:
    def build_unknown_response(self, raw_text: str) -> JarvisResponse:
        return JarvisResponse(
            command_type=JarvisCommandType.UNKNOWN,
            title="Unbekanntes Jarvis-Kommando",
            summary=(
                "Das Kommando konnte noch keinem offiziellen Phase-12.1-Typ "
                "zugeordnet werden."
            ),
            details=[
                f"Eingabe: {raw_text.strip() or '-'}",
            ],
            warnings=[],
            evidence_sections=[],
            recommended_next_steps=[
                "Formuliere die Anfrage als Systemstatus, Review, blocked jobs, KPI, Feedback, Runtime oder Vacation.",
            ],
        )

    def build_simple_response(
        self,
        *,
        command_type: JarvisCommandType,
        title: str,
        summary: str,
        details: list[str] | None = None,
        warnings: list[str] | None = None,
        evidence_sections: list[dict[str, object]] | None = None,
        recommended_next_steps: list[str] | None = None,
    ) -> JarvisResponse:
        return JarvisResponse(
            command_type=command_type,
            title=title,
            summary=summary,
            details=details or [],
            warnings=warnings or [],
            evidence_sections=evidence_sections or [],
            recommended_next_steps=recommended_next_steps or [],
        )