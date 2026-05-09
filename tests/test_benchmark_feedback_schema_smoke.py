import pytest
import tempfile
from pathlib import Path
from models.feedback_entry import FeedbackEntry, FeedbackSeverity, FeedbackCategory
from models.benchmark_session import BenchmarkSession
from core.benchmark_repository import BenchmarkRepository

# ── FeedbackEntry Tests ─────────────────────────────────────────

def test_feedback_entry_creation():
    entry = FeedbackEntry(
        feedback_id=FeedbackEntry.new_id(),
        job_id="job_test_001",
        channel="gaming_main",
        quality_mode="pro",
        timestamp_start=15.0,
        timestamp_end=18.5,
        category=FeedbackCategory.CUT_WRONG,
        severity=FeedbackSeverity.CRITICAL,
        description="Frage an Nils geschnitten, Antwort fehlt",
        speaker="me",
        game="rocket_league",
    )
    assert entry.category == FeedbackCategory.CUT_WRONG
    assert entry.severity == FeedbackSeverity.CRITICAL
    assert entry.timestamp_start == 15.0

def test_feedback_entry_to_dict_from_dict_roundtrip():
    entry = FeedbackEntry(
        feedback_id=FeedbackEntry.new_id(),
        job_id="job_test_002",
        channel="gaming_main",
        quality_mode="pro",
        timestamp_start=60.0,
        timestamp_end=None,
        category=FeedbackCategory.AUDIO_ISSUE,
        severity=FeedbackSeverity.MAJOR,
        description="Audio-Knacken bei Schnitt",
        speaker="me",
    )
    d = entry.to_dict()
    restored = FeedbackEntry.from_dict(d)
    assert restored.feedback_id == entry.feedback_id
    assert restored.category == entry.category
    assert restored.severity == entry.severity
    assert restored.timestamp_end is None

def test_feedback_entry_all_categories_valid():
    for cat in FeedbackCategory:
        assert isinstance(cat.value, str)

def test_feedback_entry_all_severities_valid():
    for sev in FeedbackSeverity:
        assert isinstance(sev.value, str)

# ── BenchmarkSession Tests ───────────────────────────────────────

def test_benchmark_session_new():
    session = BenchmarkSession.new(
        job_id="job_test_003",
        channel="gaming_main",
        quality_mode="pro",
        video_file="job_test_003_v1_final.mp4",
        reviewer="cayby",
    )
    assert session.job_id == "job_test_003"
    assert len(session.entries) == 0
    assert session.quality_score() == 1.0

def test_benchmark_session_add_entries():
    session = BenchmarkSession.new(
        job_id="job_test_004",
        channel="gaming_main",
        quality_mode="pro",
        video_file="test.mp4",
    )
    session.add(
        timestamp_start=23.0,
        category=FeedbackCategory.DEAD_TIME_LEFT_IN,
        severity=FeedbackSeverity.MAJOR,
        description="Erste 23 Sekunden waren unnötig drin",
    )
    session.add(
        timestamp_start=75.0,
        timestamp_end=80.0,
        category=FeedbackCategory.CONVERSATION_BROKEN,
        severity=FeedbackSeverity.CRITICAL,
        description="Frage an Nils wurde geschnitten, Antwort fehlt",
        speaker="me",
    )
    session.add(
        timestamp_start=120.0,
        category=FeedbackCategory.CUT_GOOD,
        severity=FeedbackSeverity.GREAT,
        description="Dieser Schnitt war perfekt — guter Rhythmus",
    )
    assert len(session.entries) == 3
    assert session.has_critical() is True
    assert len(session.critical_entries()) == 1
    assert len(session.positive_entries()) == 1
    assert len(session.problem_entries()) == 2

def test_benchmark_session_quality_score_range():
    session = BenchmarkSession.new(
        job_id="job_test_005",
        channel="gaming_main",
        quality_mode="pro",
        video_file="test.mp4",
    )
    session.add(0.0, FeedbackCategory.AUDIO_ISSUE, FeedbackSeverity.CRITICAL, "test")
    score = session.quality_score()
    assert 0.0 <= score <= 1.0

def test_benchmark_session_count_by_severity():
    session = BenchmarkSession.new(
        job_id="job_test_006",
        channel="gaming_main",
        quality_mode="pro",
        video_file="test.mp4",
    )
    session.add(0.0, FeedbackCategory.CUT_WRONG, FeedbackSeverity.MAJOR, "a")
    session.add(1.0, FeedbackCategory.CUT_WRONG, FeedbackSeverity.MAJOR, "b")
    session.add(2.0, FeedbackCategory.CUT_GOOD, FeedbackSeverity.GREAT, "c")
    counts = session.count_by_severity()
    assert counts["major"] == 2
    assert counts["great"] == 1

def test_benchmark_session_to_dict_from_dict_roundtrip():
    session = BenchmarkSession.new(
        job_id="job_test_007",
        channel="gaming_main",
        quality_mode="pro",
        video_file="test.mp4",
    )
    session.add(5.0, FeedbackCategory.ZOOM_WRONG, FeedbackSeverity.MINOR, "Zoom ruckelte")
    d = session.to_dict()
    restored = BenchmarkSession.from_dict(d)
    assert restored.session_id == session.session_id
    assert len(restored.entries) == 1
    assert restored.entries[0].category == FeedbackCategory.ZOOM_WRONG

# ── BenchmarkRepository Tests ────────────────────────────────────

def test_benchmark_repository_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = BenchmarkRepository(base_dir=Path(tmpdir))
        session = BenchmarkSession.new(
            job_id="job_repo_001",
            channel="gaming_main",
            quality_mode="pro",
            video_file="test.mp4",
        )
        session.add(10.0, FeedbackCategory.FACECAM_WRONG, FeedbackSeverity.MAJOR,
                    "Facecam war zu klein bei Reaktion")
        path = repo.save(session)
        assert path.exists()

        loaded = repo.load("job_repo_001", session.session_id)
        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert len(loaded.entries) == 1
        assert loaded.entries[0].category == FeedbackCategory.FACECAM_WRONG

def test_benchmark_repository_load_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = BenchmarkRepository(base_dir=Path(tmpdir))
        result = repo.load("nonexistent_job", "nonexistent_session")
        assert result is None

def test_benchmark_repository_list_sessions_for_job():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = BenchmarkRepository(base_dir=Path(tmpdir))
        for i in range(3):
            s = BenchmarkSession.new(
                job_id="job_list_test",
                channel="gaming_main",
                quality_mode="pro",
                video_file=f"test_{i}.mp4",
            )
            s.add(float(i), FeedbackCategory.OTHER, FeedbackSeverity.OK, f"test {i}")
            repo.save(s)
        sessions = repo.list_sessions_for_job("job_list_test")
        assert len(sessions) == 3

def test_benchmark_repository_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = BenchmarkRepository(base_dir=Path(tmpdir))
        session = BenchmarkSession.new(
            job_id="job_del_test",
            channel="gaming_main",
            quality_mode="pro",
            video_file="test.mp4",
        )
        repo.save(session)
        deleted = repo.delete("job_del_test", session.session_id)
        assert deleted is True
        assert repo.load("job_del_test", session.session_id) is None
