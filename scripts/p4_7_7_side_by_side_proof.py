"""Create side-by-side visual proof frames for P4.7 final verification."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

import cv2
import numpy as np


@dataclass(frozen=True)
class RenderSegment:
    source_start: float
    source_end: float
    output_start: float

    @property
    def duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)

    def contains(self, timestamp: float) -> bool:
        return self.source_start <= timestamp <= self.source_end

    def map_to_output(self, timestamp: float) -> float:
        return self.output_start + max(0.0, timestamp - self.source_start)


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-16", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def parse_render_segments(log_path: Path) -> list[RenderSegment]:
    time_re = re.compile(r"\[TIME\]\s+([0-9.]+)s\s+->\s+([0-9.]+)s")
    segments: list[RenderSegment] = []
    output_cursor = 0.0
    for line in _read_text(log_path).splitlines():
        match = time_re.search(line)
        if not match:
            continue
        start = float(match.group(1))
        end = float(match.group(2))
        segment = RenderSegment(source_start=start, source_end=end, output_start=output_cursor)
        segments.append(segment)
        output_cursor += segment.duration
    return segments


def parse_render_consumption(log_path: Path) -> dict:
    text = _read_text(log_path)
    layout_counts: dict[str, int] = {}
    for match in re.finditer(r"layout_kind='([^']+)'", text):
        layout = match.group(1)
        layout_counts[layout] = layout_counts.get(layout, 0) + 1
    return {
        "layout_counts": layout_counts,
        "reactive_zoom_mentions": len(re.findall(r"Found\s+\d+\s+zoom", text)),
        "low_intensity_zoom_mentions": len(re.findall(r"all low intensity", text)),
        "audio_peak_zoom_mentions": len(re.findall(r"Raw peaks:\s+[1-9]\d*", text)),
        "gameplay_pip_mentions": len(re.findall(r"GAMEPLAY \+ Facecam PiP", text)),
        "explicit_focus_layout_seen": any(
            key in layout_counts
            for key in (
                "facecam_focus",
                "gameplay_focus",
                "facecam_zoom",
                "gameplay_zoom",
            )
        ),
    }


def _load_decisions(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data.get("focus_decisions") or data.get("decisions") or []
    if isinstance(data, list):
        return data
    return []


def _in_segments(timestamp: float, segments: list[RenderSegment]) -> bool:
    return not segments or any(segment.contains(timestamp) for segment in segments)


def _map_timestamp(timestamp: float, segments: list[RenderSegment]) -> float:
    for segment in segments:
        if segment.contains(timestamp):
            return segment.map_to_output(timestamp)
    return timestamp


def _first_matching(decisions: list[dict], segments: list[RenderSegment], predicate) -> dict | None:
    for decision in decisions:
        timestamp = float(decision.get("timestamp", -1.0))
        if timestamp < 0 or not _in_segments(timestamp, segments):
            continue
        if predicate(decision):
            return decision
    return None


def choose_markers(decisions: list[dict], segments: list[RenderSegment]) -> list[tuple[str, dict]]:
    predicates = [
        (
            "voice_bruellen",
            lambda d: "bruellen" in str(d.get("reasoning", "")).lower()
            or float(d.get("facecam_zoom", 0.0)) >= 1.7,
        ),
        (
            "facial_hand_on_mouth",
            lambda d: "hand_on_mouth" in str(d.get("reasoning", "")).lower(),
        ),
        (
            "friend_reaction",
            lambda d: str(d.get("reasoning", "")).lower().startswith("friend_keyword")
            or (d.get("focus_target") == "gameplay" and float(d.get("facecam_opacity", 1.0)) < 0.7),
        ),
        (
            "smooth_zoom_start",
            lambda d: float(d.get("facecam_zoom", 1.0)) != 1.0
            or float(d.get("gameplay_zoom", 1.0)) != 1.0,
        ),
    ]
    markers: list[tuple[str, dict]] = []
    seen_timestamps: set[float] = set()
    for name, predicate in predicates:
        decision = _first_matching(decisions, segments, predicate)
        if not decision:
            continue
        timestamp = float(decision.get("timestamp", -1.0))
        if timestamp in seen_timestamps:
            continue
        seen_timestamps.add(timestamp)
        markers.append((name, decision))
    return markers


def _read_frame(video_path: Path, timestamp: float):
    capture = cv2.VideoCapture(str(video_path))
    capture.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp) * 1000.0)
    ok, frame = capture.read()
    capture.release()
    return frame if ok else None


def _resize_to_height(frame, height: int):
    h, w = frame.shape[:2]
    width = max(1, int(w * (height / h)))
    return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)


def _put_label(frame, label: str):
    cv2.rectangle(frame, (0, 0), (min(frame.shape[1], 520), 54), (0, 0, 0), -1)
    cv2.putText(
        frame,
        label,
        (16, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )


def _mean_abs_diff(raw_frame, final_frame) -> float:
    target = cv2.resize(final_frame, (raw_frame.shape[1], raw_frame.shape[0]), interpolation=cv2.INTER_AREA)
    return float(np.mean(cv2.absdiff(raw_frame, target)))


def create_proof(
    raw_video: Path,
    final_video: Path,
    decision_log: Path,
    render_log: Path,
    out_dir: Path,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    segments = parse_render_segments(render_log)
    decisions = _load_decisions(decision_log)
    markers = choose_markers(decisions, segments)
    consumption = parse_render_consumption(render_log)

    proofs = []
    for name, decision in markers:
        source_ts = float(decision.get("timestamp", 0.0))
        output_ts = _map_timestamp(source_ts, segments)
        raw_frame = _read_frame(raw_video, source_ts)
        final_frame = _read_frame(final_video, output_ts)
        if raw_frame is None or final_frame is None:
            proofs.append(
                {
                    "name": name,
                    "source_timestamp": source_ts,
                    "output_timestamp": output_ts,
                    "status": "frame_read_failed",
                    "decision": decision,
                }
            )
            continue

        raw_small = _resize_to_height(raw_frame, 540)
        final_small = _resize_to_height(final_frame, 540)
        _put_label(raw_small, f"RAW source t={source_ts:.1f}s")
        _put_label(final_small, f"FINAL output t={output_ts:.1f}s")
        combined = np.hstack([raw_small, final_small])
        diff = _mean_abs_diff(raw_small, final_small)
        visible_difference = diff >= 12.0
        path = out_dir / f"{name}_compare_source_{source_ts:.1f}s_output_{output_ts:.1f}s.png"
        cv2.imwrite(str(path), combined)
        proofs.append(
            {
                "name": name,
                "source_timestamp": round(source_ts, 3),
                "output_timestamp": round(output_ts, 3),
                "path": str(path),
                "mean_abs_diff": round(diff, 3),
                "visible_difference": bool(visible_difference),
                "decision": decision,
            }
        )

    visible = sum(1 for item in proofs if item.get("visible_difference"))
    payload = {
        "raw_video": str(raw_video),
        "final_video": str(final_video),
        "decision_log": str(decision_log),
        "render_log": str(render_log),
        "render_segments": len(segments),
        "decision_count": len(decisions),
        "proof_count": len(proofs),
        "visible_difference_count": visible,
        "visible_difference_ratio": round(visible / len(proofs), 3) if proofs else 0.0,
        "render_consumption": consumption,
        "proofs": proofs,
        "note": (
            "Visible difference compares raw composite frames to mapped final-output frames. "
            "Focus-specific render consumption is inferred separately from render log layout and zoom mentions."
        ),
    }
    (out_dir / "visual_proof_audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return payload


def _latest_job_id() -> str:
    logs = sorted(Path("data/jobs").glob("job_*_focus_decision_log.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        raise FileNotFoundError("No focus decision log found in data/jobs")
    return logs[0].name.replace("_focus_decision_log.json", "")


def _latest_final_video(job_id: str) -> Path:
    export_dir = Path("exports") / "gaming_main" / job_id
    candidates = sorted(export_dir.glob(f"{job_id}_v*_final.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        candidates = sorted(export_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No final mp4 found for {job_id}")
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", default=None)
    parser.add_argument("--raw-video", required=True)
    parser.add_argument("--final-video", default=None)
    parser.add_argument("--decision-log", default=None)
    parser.add_argument("--render-log", required=True)
    parser.add_argument("--out-dir", default="reports/phase4_7/p4_7_7_visual_proof")
    args = parser.parse_args()

    job_id = args.job_id or _latest_job_id()
    decision_log = Path(args.decision_log) if args.decision_log else Path("data/jobs") / f"{job_id}_focus_decision_log.json"
    final_video = Path(args.final_video) if args.final_video else _latest_final_video(job_id)
    create_proof(
        raw_video=Path(args.raw_video),
        final_video=final_video,
        decision_log=decision_log,
        render_log=Path(args.render_log),
        out_dir=Path(args.out_dir),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
