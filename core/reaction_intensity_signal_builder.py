from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from array import array
from dataclasses import asdict
from pathlib import Path
from typing import Any

from models.reaction_signal import (
    ReactionSignalEvidence,
    ReactionSignalThresholds,
    ReactionSignalWindow,
)


def _tool(name: str) -> str:
    candidates = [
        Path(r"D:\Tools\ffmpeg\bin") / f"{name}.exe",
        Path(r"C:\ffmpeg\bin") / f"{name}.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return name


FFMPEG = _tool("ffmpeg")
FFPROBE = _tool("ffprobe")


def parse_reaction_timestamp(value: str) -> float:
    text = value.strip()
    parts = text.split(":")

    if len(parts) == 4:
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2])
        sub = int(parts[3])
        return float(h * 3600 + m * 60 + s) + (sub / 100.0)

    if len(parts) == 3:
        h = int(parts[0])
        m = int(parts[1])
        s = float(parts[2])
        return float(h * 3600 + m * 60) + s

    if len(parts) == 2:
        m = int(parts[0])
        s = float(parts[1])
        return float(m * 60) + s

    return float(text)


def format_reaction_timestamp(seconds: float) -> str:
    total = int(seconds)
    ms = int(round((seconds - total) * 1000.0))
    if ms >= 1000:
        total += 1
        ms -= 1000
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-9))


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return -180.0
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    pos = (len(values) - 1) * pct / 100.0
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def _run(cmd: list[str], *, text: bool = False) -> bytes | str:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text)
    if p.returncode != 0:
        err = p.stderr if text else p.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(err.strip())
    return p.stdout


def _run_json(cmd: list[str]) -> dict[str, Any]:
    return json.loads(str(_run(cmd, text=True)))


def resolve_video(value: str) -> Path:
    raw = Path(value)
    if raw.exists():
        return raw.resolve()

    matches: list[Path] = []
    if not raw.is_absolute():
        for p in Path.cwd().rglob(raw.name):
            if p.is_file():
                matches.append(p)

    if not matches:
        raise FileNotFoundError(f"Video not found: {value}")

    return sorted(matches, key=lambda p: (len(str(p)), str(p).lower()))[0].resolve()


def probe_duration_seconds(video: Path) -> float:
    data = _run_json([
        FFPROBE,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video),
    ])
    return float(data["format"]["duration"])


def probe_video_size(video: Path) -> tuple[int, int]:
    data = _run_json([
        FFPROBE,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video),
    ])
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def parse_crop(value: str, video_w: int, video_h: int) -> tuple[int, int, int, int]:
    parts = [int(p.strip()) for p in value.split(",")]
    if len(parts) != 4:
        raise ValueError("Crop must be x,y,w,h")
    x, y, w, h = parts
    x = max(0, min(video_w - 1, x))
    y = max(0, min(video_h - 1, y))
    w = max(1, min(video_w - x, w))
    h = max(1, min(video_h - y, h))
    return x, y, w, h


class ReactionIntensitySignalBuilder:
    def __init__(
        self,
        *,
        video: Path,
        mic_track: int,
        gameplay_track: int,
        facecam_crop: tuple[int, int, int, int],
        audio_sample_rate: int = 8000,
        window_seconds: float = 0.5,
        facecam_fps: int = 2,
        facecam_scaled_w: int = 96,
        facecam_scaled_h: int = 54,
    ) -> None:
        self.video = video
        self.mic_track = mic_track
        self.gameplay_track = gameplay_track
        self.facecam_crop = facecam_crop
        self.audio_sample_rate = audio_sample_rate
        self.window_seconds = window_seconds
        self.facecam_fps = facecam_fps
        self.facecam_scaled_w = facecam_scaled_w
        self.facecam_scaled_h = facecam_scaled_h

    def _decode_audio_windows(self, track_1based: int) -> tuple[list[float], list[float]]:
        ordinal = track_1based - 1
        raw = _run([
            FFMPEG,
            "-hide_banner",
            "-nostdin",
            "-v", "error",
            "-i", str(self.video),
            "-map", f"0:a:{ordinal}",
            "-vn", "-sn", "-dn",
            "-ac", "1",
            "-ar", str(self.audio_sample_rate),
            "-f", "s16le",
            "pipe:1",
        ])
        assert isinstance(raw, bytes)

        samples = array("h")
        samples.frombytes(raw)
        if sys.byteorder != "little":
            samples.byteswap()

        step = max(1, int(self.audio_sample_rate * self.window_seconds))
        rms_db: list[float] = []
        peak_db: list[float] = []

        for start in range(0, len(samples) - step + 1, step):
            chunk = samples[start:start + step]
            sq = 0.0
            peak = 0
            for value in chunk:
                av = abs(value)
                if av > peak:
                    peak = av
                sq += float(value) * float(value)

            rms = math.sqrt(sq / len(chunk)) / 32768.0
            peak_norm = peak / 32768.0
            rms_db.append(_db(rms))
            peak_db.append(_db(peak_norm))

        return rms_db, peak_db

    def _decode_facecam_motion(self) -> list[float]:
        x, y, w, h = self.facecam_crop
        vf = (
            f"crop={w}:{h}:{x}:{y},"
            f"scale={self.facecam_scaled_w}:{self.facecam_scaled_h},"
            f"fps={self.facecam_fps},format=gray"
        )

        raw = _run([
            FFMPEG,
            "-hide_banner",
            "-nostdin",
            "-v", "error",
            "-i", str(self.video),
            "-map", "0:v:0",
            "-vf", vf,
            "-an", "-sn", "-dn",
            "-f", "rawvideo",
            "pipe:1",
        ])
        assert isinstance(raw, bytes)

        frame_size = self.facecam_scaled_w * self.facecam_scaled_h
        frame_count = len(raw) // frame_size
        if frame_count <= 1:
            return [0.0]

        motion = [0.0]
        prev = raw[0:frame_size]

        for i in range(1, frame_count):
            cur = raw[i * frame_size:(i + 1) * frame_size]
            diff_sum = 0
            for a, b in zip(cur, prev):
                diff_sum += abs(a - b)
            motion.append((diff_sum / frame_size) / 255.0)
            prev = cur

        return motion

    def extract_video_features(self) -> dict[str, Any]:
        mic_rms, mic_peak = self._decode_audio_windows(self.mic_track)
        gameplay_rms, gameplay_peak = self._decode_audio_windows(self.gameplay_track)
        motion_raw = self._decode_facecam_motion()

        usable = min(len(mic_rms), len(mic_peak), len(gameplay_rms), len(gameplay_peak), len(motion_raw))
        mic_rms = mic_rms[:usable]
        mic_peak = mic_peak[:usable]
        gameplay_rms = gameplay_rms[:usable]
        gameplay_peak = gameplay_peak[:usable]
        motion_raw = motion_raw[:usable]

        mic_floor = _percentile(mic_rms, 20)
        mic_active_threshold = max(mic_floor + 6.0, -55.0)
        active_rms = [v for v in mic_rms if v >= mic_active_threshold]
        active_peak = [p for r, p in zip(mic_rms, mic_peak) if r >= mic_active_threshold]
        if len(active_rms) < 10:
            active_rms = mic_rms
            active_peak = mic_peak

        gameplay_floor = _percentile(gameplay_rms, 20)
        gameplay_active_threshold = max(gameplay_floor + 6.0, -55.0)
        gameplay_active = [v for v in gameplay_rms if v >= gameplay_active_threshold]
        if len(gameplay_active) < 10:
            gameplay_active = gameplay_rms

        motion_p50 = _percentile(motion_raw, 50)
        motion_p90 = _percentile(motion_raw, 90)

        return {
            "mic_rms_db": mic_rms,
            "mic_peak_db": mic_peak,
            "gameplay_rms_db": gameplay_rms,
            "gameplay_peak_db": gameplay_peak,
            "facecam_motion_raw": motion_raw,
            "baselines": {
                "mic_floor_dbfs_p20": round(mic_floor, 4),
                "mic_active_threshold_dbfs": round(mic_active_threshold, 4),
                "mic_normal_rms_dbfs": round(_percentile(active_rms, 50), 4),
                "mic_normal_peak_dbfs": round(_percentile(active_peak, 50), 4),
                "gameplay_floor_dbfs_p20": round(gameplay_floor, 4),
                "gameplay_active_threshold_dbfs": round(gameplay_active_threshold, 4),
                "gameplay_normal_rms_dbfs": round(_percentile(gameplay_active, 50), 4),
                "facecam_motion_p50": round(motion_p50, 8),
                "facecam_motion_p90": round(motion_p90, 8),
            },
        }

    def evidence_at(
        self,
        features: dict[str, Any],
        time_seconds: float,
        *,
        tolerance_seconds: float = 1.5,
    ) -> ReactionSignalEvidence:
        baselines = features["baselines"]
        mic_rms = features["mic_rms_db"]
        mic_peak = features["mic_peak_db"]
        gameplay_rms = features["gameplay_rms_db"]
        gameplay_peak = features["gameplay_peak_db"]
        motion_raw = features["facecam_motion_raw"]

        center = int(round(time_seconds / self.window_seconds))
        radius = max(1, int(round(tolerance_seconds / self.window_seconds)))
        lo = max(0, center - radius)
        hi = min(len(mic_rms), center + radius + 1)

        mic_rms_max = max(mic_rms[lo:hi])
        mic_peak_max = max(mic_peak[lo:hi])
        gameplay_rms_max = max(gameplay_rms[lo:hi])
        gameplay_peak_max = max(gameplay_peak[lo:hi])
        motion_max = max(motion_raw[lo:hi])

        mic_rise = mic_rms_max - float(baselines["mic_normal_rms_dbfs"])
        mic_peak_over = mic_peak_max - float(baselines["mic_normal_peak_dbfs"])
        gameplay_rise = gameplay_rms_max - float(baselines["gameplay_normal_rms_dbfs"])

        motion_p50 = float(baselines["facecam_motion_p50"])
        motion_p90 = float(baselines["facecam_motion_p90"])
        facecam_change = _clamp01((motion_max - motion_p50) / max(0.0001, motion_p90 - motion_p50))

        audio_norm = _clamp01((mic_rise - 4.0) / 9.0)
        peak_norm = _clamp01((mic_peak_over - 6.0) / 14.0)
        fusion = (0.78 * audio_norm) + (0.07 * peak_norm) + (0.15 * facecam_change)

        return ReactionSignalEvidence(
            time_seconds=round(time_seconds, 3),
            timestamp=format_reaction_timestamp(time_seconds),
            mic_audio_rise_db=round(mic_rise, 3),
            mic_peak_over_baseline_db=round(mic_peak_over, 3),
            facecam_change=round(facecam_change, 4),
            gameplay_rise_db=round(gameplay_rise, 3),
            gameplay_peak_dbfs=round(gameplay_peak_max, 3),
            fusion_score=round(fusion, 4),
            g6_state="not_loaded_stage_d_probe",
            g6_intensity=0.0,
        )

    def classify(self, evidence: ReactionSignalEvidence, thresholds: ReactionSignalThresholds) -> ReactionSignalWindow:
        event = (
            evidence.mic_audio_rise_db >= thresholds.event_mic_rise_db
            and evidence.fusion_score >= thresholds.event_fusion_score
        )

        if not event:
            intensity = "none"
            confidence = max(0.0, min(0.49, evidence.fusion_score))
        elif evidence.mic_audio_rise_db >= thresholds.high_mic_rise_db:
            intensity = "high"
            confidence = _clamp01(0.72 + ((evidence.mic_audio_rise_db - thresholds.high_mic_rise_db) / 10.0))
        elif evidence.mic_audio_rise_db >= thresholds.medium_mic_rise_db:
            intensity = "medium"
            confidence = _clamp01(0.58 + ((evidence.mic_audio_rise_db - thresholds.medium_mic_rise_db) / 8.0))
        else:
            intensity = "low"
            confidence = _clamp01(0.50 + ((evidence.mic_audio_rise_db - thresholds.event_mic_rise_db) / 8.0))

        return ReactionSignalWindow(
            time_seconds=evidence.time_seconds,
            timestamp=evidence.timestamp,
            reaction_event=bool(event),
            reaction_intensity=intensity,
            confidence=round(confidence, 4),
            evidence=evidence,
        )

    def calibrate_thresholds(
        self,
        features: dict[str, Any],
        ground_truth: list[dict[str, Any]],
    ) -> ReactionSignalThresholds:
        usable_marks: list[dict[str, Any]] = []
        for item in ground_truth:
            if item["label"] == "dont_care":
                continue
            seconds = parse_reaction_timestamp(item["timestamp"])
            ev = self.evidence_at(features, seconds, tolerance_seconds=1.5)
            usable_marks.append({**item, "seconds": seconds, "evidence": ev})

        positives = [m for m in usable_marks if m["label"] == "reaction"]
        high_medium = [
            m for m in positives
            if str(m.get("intensity", "")).lower() in {"high", "medium"}
        ]
        negatives = [m for m in usable_marks if m["label"] == "negative"]

        best: tuple[Any, ReactionSignalThresholds] | None = None

        rise_values = [round(5.5 + i * 0.25, 2) for i in range(31)]
        fusion_values = [round(0.34 + i * 0.02, 2) for i in range(19)]

        for rise_thr in rise_values:
            for fusion_thr in fusion_values:
                thresholds = ReactionSignalThresholds(
                    event_mic_rise_db=rise_thr,
                    event_fusion_score=fusion_thr,
                    medium_mic_rise_db=rise_thr + 1.4,
                    high_mic_rise_db=rise_thr + 3.0,
                    facecam_motion_hint=0.60,
                    precision_negative_false_positive_count=0,
                    high_medium_recall_ratio=0.0,
                    any_reaction_recall_ratio=0.0,
                )

                pos_hit = 0
                hm_hit = 0
                neg_fp = 0

                for mark in positives:
                    win = self.classify(mark["evidence"], thresholds)
                    if win.reaction_event:
                        pos_hit += 1

                for mark in high_medium:
                    win = self.classify(mark["evidence"], thresholds)
                    if win.reaction_event:
                        hm_hit += 1

                for mark in negatives:
                    win = self.classify(mark["evidence"], thresholds)
                    if win.reaction_event:
                        neg_fp += 1

                any_recall = pos_hit / max(1, len(positives))
                hm_recall = hm_hit / max(1, len(high_medium))

                candidate = ReactionSignalThresholds(
                    event_mic_rise_db=rise_thr,
                    event_fusion_score=fusion_thr,
                    medium_mic_rise_db=rise_thr + 1.4,
                    high_mic_rise_db=rise_thr + 3.0,
                    facecam_motion_hint=0.60,
                    precision_negative_false_positive_count=neg_fp,
                    high_medium_recall_ratio=round(hm_recall, 4),
                    any_reaction_recall_ratio=round(any_recall, 4),
                )

                precision_ok = 1 if neg_fp == 0 else 0
                score = (
                    precision_ok,
                    -neg_fp,
                    round(hm_recall, 6),
                    round(any_recall, 6),
                    rise_thr,
                    fusion_thr,
                )

                if best is None or score > best[0]:
                    best = (score, candidate)

        if best is None:
            raise RuntimeError("Could not calibrate reaction thresholds.")

        return best[1]

    def build_window_rows(
        self,
        features: dict[str, Any],
        thresholds: ReactionSignalThresholds,
    ) -> list[ReactionSignalWindow]:
        count = min(
            len(features["mic_rms_db"]),
            len(features["gameplay_rms_db"]),
            len(features["facecam_motion_raw"]),
        )
        rows: list[ReactionSignalWindow] = []
        for idx in range(count):
            t = idx * self.window_seconds
            ev = self.evidence_at(features, t, tolerance_seconds=0.0)
            rows.append(self.classify(ev, thresholds))
        return rows

    def evaluate_ground_truth(
        self,
        features: dict[str, Any],
        thresholds: ReactionSignalThresholds,
        ground_truth: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in ground_truth:
            seconds = parse_reaction_timestamp(item["timestamp"])
            ev = self.evidence_at(features, seconds, tolerance_seconds=1.5)
            win = self.classify(ev, thresholds)

            label = item["label"]
            if label == "reaction":
                passed = win.reaction_event
            elif label == "negative":
                passed = not win.reaction_event
            else:
                passed = True

            rows.append({
                **item,
                "seconds": round(seconds, 3),
                "detected_event": win.reaction_event,
                "detected_intensity": win.reaction_intensity,
                "confidence": win.confidence,
                "pass": bool(passed),
                "evidence": ev.to_dict(),
            })
        return rows

    def find_gameplay_honesty_check(
        self,
        features: dict[str, Any],
        thresholds: ReactionSignalThresholds,
        negative_marks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        for item in negative_marks:
            seconds = parse_reaction_timestamp(item["timestamp"])
            ev = self.evidence_at(features, seconds, tolerance_seconds=1.5)
            win = self.classify(ev, thresholds)
            candidates.append({
                "source": item.get("source", ""),
                "timestamp": item["timestamp"],
                "seconds": round(seconds, 3),
                "detected_event": win.reaction_event,
                "detected_intensity": win.reaction_intensity,
                "confidence": win.confidence,
                "gameplay_peak_dbfs": ev.gameplay_peak_dbfs,
                "gameplay_rise_db": ev.gameplay_rise_db,
                "mic_audio_rise_db": ev.mic_audio_rise_db,
                "pass": not win.reaction_event,
                "evidence": ev.to_dict(),
            })

        if not candidates:
            raise RuntimeError("No negative marks available for gameplay honesty check.")

        return sorted(candidates, key=lambda c: (c["gameplay_peak_dbfs"], c["gameplay_rise_db"]), reverse=True)[0]


def summarize_distribution(
    rows: list[ReactionSignalWindow],
    *,
    window_seconds: float,
) -> dict[str, Any]:
    total = len(rows)
    events = [r for r in rows if r.reaction_event]
    by_intensity = {
        "none": sum(1 for r in rows if r.reaction_intensity == "none"),
        "low": sum(1 for r in rows if r.reaction_intensity == "low"),
        "medium": sum(1 for r in rows if r.reaction_intensity == "medium"),
        "high": sum(1 for r in rows if r.reaction_intensity == "high"),
    }

    return {
        "window_count": total,
        "window_seconds": round(window_seconds, 4),
        "reaction_event_windows": len(events),
        "reaction_event_ratio": round(len(events) / max(1, total), 5),
        "by_intensity": by_intensity,
    }


def threshold_dict(thresholds: ReactionSignalThresholds) -> dict[str, Any]:
    return asdict(thresholds)
