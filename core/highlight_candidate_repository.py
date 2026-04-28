from __future__ import annotations

import json
from pathlib import Path

from models.edit_signal import EditSignal
from models.highlight_candidate import HighlightCandidate


class HighlightCandidateRepository:
    def _file_path(self, export_path: str | Path) -> Path:
        return Path(export_path) / "highlight_intelligence.json"

    def _signal_to_dict(self, signal: EditSignal) -> dict:
        return {
            "signal_id": signal.signal_id,
            "job_id": signal.job_id,
            "start_time": signal.start_time,
            "end_time": signal.end_time,
            "signal_type": signal.signal_type,
            "strength": signal.strength,
            "confidence": signal.confidence,
            "tags": list(signal.tags),
            "source": signal.source,
            "notes": list(signal.notes),
            "metadata": dict(signal.metadata),
            "created_at": signal.created_at,
            "updated_at": signal.updated_at,
        }

    def _candidate_to_dict(self, candidate: HighlightCandidate) -> dict:
        return {
            "candidate_id": candidate.candidate_id,
            "job_id": candidate.job_id,
            "start_time": candidate.start_time,
            "end_time": candidate.end_time,
            "highlight_score": candidate.highlight_score,
            "candidate_kind": candidate.candidate_kind,
            "confidence": candidate.confidence,
            "signal_tags": list(candidate.signal_tags),
            "source": candidate.source,
            "notes": list(candidate.notes),
            "created_at": candidate.created_at,
            "updated_at": candidate.updated_at,
        }

    def _signal_from_dict(self, data: dict) -> EditSignal:
        return EditSignal(
            signal_id=str(data.get("signal_id")),
            job_id=str(data.get("job_id")),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            signal_type=str(data.get("signal_type", "unknown")),
            strength=float(data.get("strength", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            tags=list(data.get("tags", [])),
            source=data.get("source"),
            notes=list(data.get("notes", [])),
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def _candidate_from_dict(self, data: dict) -> HighlightCandidate:
        return HighlightCandidate(
            candidate_id=str(data.get("candidate_id")),
            job_id=str(data.get("job_id")),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            highlight_score=float(data.get("highlight_score", 0.0)),
            candidate_kind=str(data.get("candidate_kind", "unknown")),
            confidence=float(data.get("confidence", 0.0)),
            signal_tags=list(data.get("signal_tags", [])),
            source=data.get("source"),
            notes=list(data.get("notes", [])),
            created_at=str(data.get("created_at")),
            updated_at=str(data.get("updated_at")),
        )

    def save_result(
        self,
        export_path: str | Path,
        *,
        edit_signals: list[EditSignal],
        highlight_candidates: list[HighlightCandidate],
        weak_zones: list[HighlightCandidate],
        summary: dict,
    ) -> str:
        file_path = self._file_path(export_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "edit_signals": [self._signal_to_dict(signal) for signal in edit_signals],
            "highlight_candidates": [
                self._candidate_to_dict(candidate)
                for candidate in highlight_candidates
            ],
            "weak_zones": [
                self._candidate_to_dict(candidate)
                for candidate in weak_zones
            ],
            "summary": dict(summary),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        return str(file_path)

    def load_result(self, export_path: str | Path) -> dict[str, object]:
        file_path = self._file_path(export_path)

        if not file_path.exists():
            return {
                "edit_signals": [],
                "highlight_candidates": [],
                "weak_zones": [],
                "summary": {},
            }

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            "edit_signals": [
                self._signal_from_dict(item)
                for item in data.get("edit_signals", [])
            ],
            "highlight_candidates": [
                self._candidate_from_dict(item)
                for item in data.get("highlight_candidates", [])
            ],
            "weak_zones": [
                self._candidate_from_dict(item)
                for item in data.get("weak_zones", [])
            ],
            "summary": dict(data.get("summary", {})),
        }