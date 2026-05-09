from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import uuid
import json
from datetime import datetime, timezone
from models.feedback_entry import FeedbackEntry, FeedbackSeverity, FeedbackCategory


@dataclass
class BenchmarkSession:
    """
    Eine vollständige Bewertungssession für ein gerendertes Video.
    Enthält alle FeedbackEntries zu einem Job.
    """
    session_id: str
    job_id: str
    channel: str
    quality_mode: str
    video_file: str                        # Dateiname des bewerteten Output-Videos
    created_at: str                        # ISO-8601 UTC
    reviewer: str                          # z.B. "cayby" oder "auto"
    entries: List[FeedbackEntry] = field(default_factory=list)
    notes: Optional[str] = None

    # ── Mutationen ────────────────────────────────────────────────

    def add_entry(self, entry: FeedbackEntry) -> None:
        """Fügt einen FeedbackEntry hinzu."""
        self.entries.append(entry)

    def add(
        self,
        timestamp_start: float,
        category: FeedbackCategory,
        severity: FeedbackSeverity,
        description: str,
        timestamp_end: Optional[float] = None,
        speaker: Optional[str] = None,
        game: Optional[str] = None,
        notes: Optional[str] = None,
        source_timestamp_start: Optional[float] = None,
        source_timestamp_end: Optional[float] = None,
    ) -> FeedbackEntry:
        """Shortcut: Erstellt und speichert einen FeedbackEntry in einem Schritt."""
        entry = FeedbackEntry(
            feedback_id=FeedbackEntry.new_id(),
            job_id=self.job_id,
            channel=self.channel,
            quality_mode=self.quality_mode,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
            category=category,
            severity=severity,
            description=description,
            speaker=speaker,
            game=game,
            notes=notes,
            source_timestamp_start=source_timestamp_start,
            source_timestamp_end=source_timestamp_end,
        )
        self.entries.append(entry)
        return entry

    # ── Statistiken ───────────────────────────────────────────────

    def count_by_severity(self) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in FeedbackSeverity}
        for e in self.entries:
            counts[e.severity.value] += 1
        return counts

    def count_by_category(self) -> dict[str, int]:
        counts: dict[str, int] = {c.value: 0 for c in FeedbackCategory}
        for e in self.entries:
            counts[e.category.value] += 1
        return counts

    def has_critical(self) -> bool:
        return any(e.severity == FeedbackSeverity.CRITICAL for e in self.entries)

    def critical_entries(self) -> List[FeedbackEntry]:
        return [e for e in self.entries if e.severity == FeedbackSeverity.CRITICAL]

    def positive_entries(self) -> List[FeedbackEntry]:
        return [e for e in self.entries
                if e.severity in (FeedbackSeverity.GOOD, FeedbackSeverity.GREAT)]

    def problem_entries(self) -> List[FeedbackEntry]:
        return [e for e in self.entries
                if e.severity in (FeedbackSeverity.CRITICAL, FeedbackSeverity.MAJOR, FeedbackSeverity.MINOR)]

    def quality_score(self) -> float:
        """
        Einfacher Score 0.0–1.0 basierend auf Severity-Gewichtung.
        1.0 = alles GREAT, 0.0 = nur CRITICAL.
        Gibt 1.0 zurück wenn keine Einträge vorhanden.
        """
        if not self.entries:
            return 1.0
        weights = {
            FeedbackSeverity.CRITICAL: -2.0,
            FeedbackSeverity.MAJOR:    -1.0,
            FeedbackSeverity.MINOR:    -0.3,
            FeedbackSeverity.OK:        0.0,
            FeedbackSeverity.GOOD:      0.5,
            FeedbackSeverity.GREAT:     1.0,
        }
        raw = sum(weights[e.severity] for e in self.entries)
        max_possible = len(self.entries) * 1.0
        min_possible = len(self.entries) * -2.0
        if max_possible == min_possible:
            return 1.0
        normalized = (raw - min_possible) / (max_possible - min_possible)
        return round(max(0.0, min(1.0, normalized)), 4)

    # ── Serialisierung ────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "session_id":  self.session_id,
            "job_id":      self.job_id,
            "channel":     self.channel,
            "quality_mode":self.quality_mode,
            "video_file":  self.video_file,
            "created_at":  self.created_at,
            "reviewer":    self.reviewer,
            "notes":       self.notes,
            "entries":     [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BenchmarkSession":
        session = cls(
            session_id= data["session_id"],
            job_id=     data["job_id"],
            channel=    data["channel"],
            quality_mode=data["quality_mode"],
            video_file= data["video_file"],
            created_at= data["created_at"],
            reviewer=   data["reviewer"],
            notes=      data.get("notes"),
        )
        session.entries = [FeedbackEntry.from_dict(e) for e in data.get("entries", [])]
        return session

    @staticmethod
    def new(
        job_id: str,
        channel: str,
        quality_mode: str,
        video_file: str,
        reviewer: str = "cayby",
        notes: Optional[str] = None,
    ) -> "BenchmarkSession":
        return BenchmarkSession(
            session_id=  str(uuid.uuid4()),
            job_id=      job_id,
            channel=     channel,
            quality_mode=quality_mode,
            video_file=  video_file,
            created_at=  datetime.now(timezone.utc).isoformat(),
            reviewer=    reviewer,
            notes=       notes,
        )
