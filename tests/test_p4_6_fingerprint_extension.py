from __future__ import annotations

import json
from pathlib import Path

from scripts.extend_p4_6_fingerprints import (
    CorpusFingerprintEntry,
    P46FingerprintExtender,
    audit_extensions,
    discover_entries,
    entry_needs_extension,
)


def _base_fingerprint(video_id: str, video_type: str = "gaming_main") -> dict:
    return {
        "video_id": video_id,
        "type": video_type,
        "quality_tier": "top",
        "ingest_version": "1",
        "ingest_timestamp_utc": "2026-05-24T00:00:00Z",
        "transcript": {"language": "unknown", "segments_count": 0, "first_10s_text": ""},
        "scene_changes": {"count": 0, "rate_per_minute": 0.0, "boundaries_seconds": []},
        "audio": {"lufs_integrated": 0.0, "rms_curve_sampled": [], "peak_db": 0.0},
        "pacing": {
            "cut_count": 0,
            "cuts_per_minute": 0.0,
            "median_clip_seconds": 0.0,
            "clip_length_histogram_bins": [],
        },
        "hook": {"first_words": "", "pattern_class": "unknown"},
        "reaction_timing": {"applicable": False},
    }


class FakeVoiceAnalyzer:
    def analyze(self, video_path: str, speaker: str = "ali"):
        return [object(), object()]

    def distribution(self, points):
        return {"normal": 50.0, "leise_erhoeht": 25.0, "schreien": 25.0, "bruellen": 0.0}


class FakeFaceDetector:
    def detect_in_video(self, video_path: str, sample_rate_fps: float, max_samples=None):
        return [object()]

    def close(self):
        pass


class FakeExpressionAnalyzer:
    def analyze_video(self, points):
        return [object()]

    def distribution(self, points):
        return {
            "direct_gaze": 100.0,
            "hand_on_mouth": 0.0,
            "eyebrow_raised": 0.0,
            "surprise": 0.0,
            "frustration": 0.0,
            "mouth_open_yell": 0.0,
            "neutral": 0.0,
        }


class FakeGameplayDetector:
    def detect(self, video_path: str, sample_rate_fps: float, max_samples=None):
        return [object(), object(), object(), object()]

    def distribution(self, points):
        return {"gameplay": 75.0, "menu": 25.0}


class FakeAudioStreamInspector:
    def inspect(self, video_path: str):
        class Inventory:
            is_multi_track = False
            has_mic_track = False
            has_discord_track = False

        return Inventory()


def _write_fingerprint(folder: Path, video_id: str, video_type: str = "gaming_main") -> None:
    folder.mkdir(parents=True)
    (folder / "style_fingerprint.json").write_text(
        json.dumps(_base_fingerprint(video_id, video_type), indent=2),
        encoding="utf-8",
    )
    (folder / "final.mp4").write_bytes(b"video")


def test_discover_entries_prefers_pair_raw_for_pairs(tmp_path: Path) -> None:
    pair = tmp_path / "pairs" / "pair_001"
    _write_fingerprint(pair, "pair_001")
    (pair / "raw.mp4").write_bytes(b"raw")
    top = tmp_path / "top_solo" / "video_001"
    _write_fingerprint(top, "video_001")

    entries = discover_entries(tmp_path)

    assert len(entries) == 2
    assert entries[0].source_video_path.name == "raw.mp4"
    assert entries[1].source_video_path.name == "final.mp4"


def test_extend_pair_fingerprint_adds_all_p4_6_fields(tmp_path: Path) -> None:
    pair = tmp_path / "pairs" / "pair_001"
    _write_fingerprint(pair, "pair_001")
    (pair / "raw.mp4").write_bytes(b"raw")
    entry = CorpusFingerprintEntry(
        folder=pair,
        bucket="pairs",
        video_id="pair_001",
        fingerprint_path=pair / "style_fingerprint.json",
        source_video_path=pair / "raw.mp4",
        raw_video_path=pair / "raw.mp4",
        has_raw=True,
    )
    extender = P46FingerprintExtender(
        voice_analyzer=FakeVoiceAnalyzer(),
        face_detector=FakeFaceDetector(),
        expression_analyzer=FakeExpressionAnalyzer(),
        gameplay_detector=FakeGameplayDetector(),
        audio_stream_inspector=FakeAudioStreamInspector(),
    )

    fingerprint = extender.extend_entry(entry)

    assert fingerprint["voice_intensity_distribution"]["schreien"] == 25.0
    assert fingerprint["facial_expression_distribution"]["direct_gaze"] == 100.0
    assert fingerprint["gameplay_ratio"]["gameplay_percent"] == 75.0
    assert fingerprint["speaker_distribution"] == {"ali": 0.0, "friend": 0.0, "unknown": 100.0}


def test_audit_rejects_speaker_distribution_on_top_solo(tmp_path: Path) -> None:
    top = tmp_path / "top_solo" / "video_001"
    _write_fingerprint(top, "video_001")
    path = top / "style_fingerprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(
        {
            "voice_intensity_distribution": {},
            "facial_expression_distribution": {},
            "gameplay_ratio": {"gameplay_percent": 50.0, "menu_percent": 50.0},
            "speaker_distribution": {"ali": 0.0, "friend": 0.0, "unknown": 100.0},
        }
    )
    path.write_text(json.dumps(data), encoding="utf-8")

    report = audit_extensions(tmp_path)

    assert report["problem_count"] == 1
    assert report["problems"][0]["problem"] == "unexpected_speaker_distribution"


def test_entry_needs_extension_false_when_required_fields_exist(tmp_path: Path) -> None:
    top = tmp_path / "top_solo" / "video_001"
    _write_fingerprint(top, "video_001")
    path = top / "style_fingerprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(
        {
            "voice_intensity_distribution": {},
            "facial_expression_distribution": {},
            "gameplay_ratio": {"gameplay_percent": 50.0, "menu_percent": 50.0},
        }
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    entry = discover_entries(tmp_path)[0]

    assert entry_needs_extension(entry) is False
