from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import uuid


class FeedbackSeverity(str, Enum):
    """Wie schwerwiegend ist das Problem oder wie gut ist der Moment?"""
    CRITICAL   = "critical"    # Harter Fehler — darf nicht passieren
    MAJOR      = "major"       # Deutlich schlechter Schnitt / Qualitätsproblem
    MINOR      = "minor"       # Kleines Problem, aber noch okay
    OK         = "ok"          # Neutral / akzeptabel
    GOOD       = "good"        # Besser als erwartet
    GREAT      = "great"       # Sehr gut — soll wiederholt werden


class FeedbackCategory(str, Enum):
    """Was ist die Art des Feedbacks?"""
    CUT_WRONG           = "cut_wrong"           # Falscher Schnitt (z.B. Frage ohne Antwort)
    CUT_GOOD            = "cut_good"            # Guter Schnitt
    AUDIO_ISSUE         = "audio_issue"         # Audio-Knacken, Verzerrung, Lautstärkesprung
    AUDIO_GOOD          = "audio_good"          # Sauberes Audio
    FACECAM_WRONG       = "facecam_wrong"       # Falsche Facecam-Entscheidung
    FACECAM_GOOD        = "facecam_good"        # Richtige Facecam-Entscheidung
    GAMEPLAY_WRONG      = "gameplay_wrong"      # Falscher Gameplay-Fokus
    GAMEPLAY_GOOD       = "gameplay_good"       # Richtiger Gameplay-Fokus
    ZOOM_WRONG          = "zoom_wrong"          # Schlechter Zoom
    ZOOM_GOOD           = "zoom_good"           # Guter Zoom
    DEAD_TIME_LEFT_IN   = "dead_time_left_in"   # Tote Stelle nicht entfernt
    DEAD_TIME_REMOVED   = "dead_time_removed"   # Tote Stelle korrekt entfernt
    CONTEXT_MISSING     = "context_missing"     # Kontext fehlt (Setup ohne Payoff)
    CONTEXT_GOOD        = "context_good"        # Kontext korrekt erhalten
    CONVERSATION_BROKEN = "conversation_broken" # Gespräch falsch aufgetrennt
    CONVERSATION_GOOD   = "conversation_good"   # Gespräch korrekt erhalten
    STORY_FLOW_BAD      = "story_flow_bad"      # Story-Fluss gestört
    STORY_FLOW_GOOD     = "story_flow_good"     # Story-Fluss gut
    OTHER               = "other"               # Sonstiges


@dataclass
class FeedbackEntry:
    """
    Ein einzelner Feedback-Eintrag für einen Zeitpunkt oder Zeitbereich
    in einem gerenderten Video.
    """
    feedback_id: str                  # UUID, automatisch generiert
    job_id: str                       # Welcher Pipeline-Job wurde bewertet?
    channel: str                      # z.B. "gaming_main"
    quality_mode: str                 # z.B. "pro"

    # Zeitstempel im gerenderten Output-Video (Sekunden)
    timestamp_start: float
    timestamp_end: Optional[float]    # None = Einzelmoment

    # Bewertung
    category: FeedbackCategory
    severity: FeedbackSeverity
    description: str                  # Freitext — was ist passiert?

    # Optional: Zeitstempel im Original-Rohmaterial
    source_timestamp_start: Optional[float] = None
    source_timestamp_end: Optional[float]   = None

    # Optional: Kontext
    speaker: Optional[str]  = None    # z.B. "me", "nils", "game_audio"
    game: Optional[str]     = None    # z.B. "rocket_league", "fortnite"
    notes: Optional[str]    = None    # Zusätzliche Notizen

    def to_dict(self) -> dict:
        return {
            "feedback_id":           self.feedback_id,
            "job_id":                self.job_id,
            "channel":               self.channel,
            "quality_mode":          self.quality_mode,
            "timestamp_start":       self.timestamp_start,
            "timestamp_end":         self.timestamp_end,
            "category":              self.category.value,
            "severity":              self.severity.value,
            "description":           self.description,
            "source_timestamp_start":self.source_timestamp_start,
            "source_timestamp_end":  self.source_timestamp_end,
            "speaker":               self.speaker,
            "game":                  self.game,
            "notes":                 self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackEntry":
        return cls(
            feedback_id=           data["feedback_id"],
            job_id=                data["job_id"],
            channel=               data["channel"],
            quality_mode=          data["quality_mode"],
            timestamp_start=       float(data["timestamp_start"]),
            timestamp_end=         float(data["timestamp_end"]) if data.get("timestamp_end") is not None else None,
            category=              FeedbackCategory(data["category"]),
            severity=              FeedbackSeverity(data["severity"]),
            description=           data["description"],
            source_timestamp_start=float(data["source_timestamp_start"]) if data.get("source_timestamp_start") is not None else None,
            source_timestamp_end=  float(data["source_timestamp_end"]) if data.get("source_timestamp_end") is not None else None,
            speaker=               data.get("speaker"),
            game=                  data.get("game"),
            notes=                 data.get("notes"),
        )

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
