"""
Demo: Phase 2.B-PRO-B — BenchmarkSession für job_e279d2d0f470
Spiegelt echte Kritikpunkte aus Phase 2.B.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from models.feedback_entry import FeedbackCategory, FeedbackSeverity
from models.benchmark_session import BenchmarkSession
from core.benchmark_repository import BenchmarkRepository

JOB_ID = "job_e279d2d0f470"

session = BenchmarkSession.new(
    job_id=JOB_ID,
    channel="gaming_main",
    quality_mode="pro",
    video_file=f"{JOB_ID}_v1_final.mp4",
    reviewer="cayby",
)

session.add(
    timestamp_start=23.0,
    category=FeedbackCategory.DEAD_TIME_LEFT_IN,
    severity=FeedbackSeverity.MAJOR,
    description="Erste 23 Sekunden drin — Runde hatte noch nicht angefangen",
)

session.add(
    timestamp_start=75.0,
    category=FeedbackCategory.CONVERSATION_BROKEN,
    severity=FeedbackSeverity.CRITICAL,
    description="Frage an Nils geschnitten — Antwort komplett weg",
    speaker="me",
)

session.add(
    timestamp_start=272.0,
    category=FeedbackCategory.AUDIO_ISSUE,
    severity=FeedbackSeverity.MAJOR,
    description="Audio klingt verzerrt nach Mini-Cut",
)

repo = BenchmarkRepository(base_dir=Path("storage") / "benchmarks")
saved_path = repo.save(session)

print(f"Session:      {session.session_id}")
print(f"Job:          {session.job_id}")
print(f"Entries:      {len(session.entries)}")
print(f"Score:        {session.quality_score()}")
print(f"Has Critical: {session.has_critical()}")
print(f"Saved to:     {saved_path}")
