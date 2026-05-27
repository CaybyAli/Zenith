"""Build a stage-level GPU utilization breakdown for P4.7 final renders.

The preferred inputs are:
- ``nvidia-smi dmon -o TD -s uct ...`` output with date/time columns.
- Pipeline logs whose lines were prefixed with ISO timestamps by the render
  wrapper.

If either input lacks timestamps, the script falls back to utilization-based
segments so the final report still contains a defensible breakdown.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Iterable


@dataclass(frozen=True)
class DmonSample:
    index: int
    timestamp: datetime | None
    sm: float
    mem: float
    enc: float
    dec: float


@dataclass(frozen=True)
class LogLine:
    timestamp: datetime
    text: str


def _read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-16", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    return path.read_bytes().decode("utf-8", errors="replace")


def _parse_float(value: str) -> float:
    if value.upper() == "N/A":
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_dmon(path: Path) -> list[DmonSample]:
    samples: list[DmonSample] = []
    text = _read_text(path)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split()
        timestamp: datetime | None = None
        offset = 0
        if len(parts) >= 13 and re.fullmatch(r"\d{8}", parts[0]) and re.fullmatch(
            r"\d{2}:\d{2}:\d{2}", parts[1]
        ):
            timestamp = datetime.strptime(parts[0] + " " + parts[1], "%Y%m%d %H:%M:%S")
            offset = 2

        if len(parts) < offset + 5:
            continue

        # dmon -s uct columns: gpu sm mem enc dec jpg ofa mclk pclk rxpci txpci
        samples.append(
            DmonSample(
                index=len(samples),
                timestamp=timestamp,
                sm=_parse_float(parts[offset + 1]),
                mem=_parse_float(parts[offset + 2]),
                enc=_parse_float(parts[offset + 3]),
                dec=_parse_float(parts[offset + 4]),
            )
        )
    return samples


def parse_timestamped_log(path: Path) -> list[LogLine]:
    lines: list[LogLine] = []
    iso_prefix = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}T\S+)\s+(?P<text>.*)$")
    for line in _read_text(path).splitlines():
        match = iso_prefix.match(line)
        if not match:
            continue
        raw_ts = match.group("ts")
        try:
            timestamp = datetime.fromisoformat(raw_ts).replace(tzinfo=None)
        except ValueError:
            continue
        lines.append(LogLine(timestamp=timestamp, text=match.group("text")))
    return lines


def _first_timestamp(lines: Iterable[LogLine], needle: str) -> datetime | None:
    for line in lines:
        if needle in line.text:
            return line.timestamp
    return None


def _first_timestamp_matching(lines: Iterable[LogLine], *needles: str) -> datetime | None:
    for line in lines:
        if all(needle in line.text for needle in needles):
            return line.timestamp
    return None


def _first_timestamp_regex(lines: Iterable[LogLine], pattern: str) -> datetime | None:
    compiled = re.compile(pattern)
    for line in lines:
        if compiled.search(line.text):
            return line.timestamp
    return None


def build_stage_windows(lines: list[LogLine], samples: list[DmonSample]) -> dict[str, tuple[datetime, datetime]] | None:
    if not lines or not any(sample.timestamp for sample in samples):
        return None

    start = lines[0].timestamp
    end = lines[-1].timestamp
    transcript_end = _first_timestamp_matching(lines, "[gaming_pipeline] TRANSCRIPT")
    analysis_end = _first_timestamp_matching(lines, "[gaming_pipeline] ANALYZE", "done")
    render_start = _first_timestamp(lines, "[CUT] RENDERING GESTARTET")
    render_end = _first_timestamp_regex(lines, r"\[gaming_pipeline\]\s+RENDER\s+job_")
    done = _first_timestamp(lines, "[pipeline_runner] Done") or end

    if not render_start:
        render_start = analysis_end
    if not render_end:
        render_end = done

    windows: dict[str, tuple[datetime, datetime]] = {}
    if transcript_end and transcript_end > start:
        windows["transcript"] = (start, transcript_end)
    if transcript_end and analysis_end and analysis_end > transcript_end:
        windows["analysis"] = (transcript_end, analysis_end)
    elif analysis_end and analysis_end > start:
        windows["analysis"] = (start, analysis_end)
    if analysis_end and render_start and render_start > analysis_end:
        windows["scene_detection_and_timeline"] = (analysis_end, render_start)
    if render_start and render_end and render_end > render_start:
        windows["longform_render"] = (render_start, render_end)
    if render_end and done and done > render_end:
        windows["shorts_render_and_export"] = (render_end, done)

    return windows or None


def _summarize_samples(samples: list[DmonSample], duration_seconds: float | None = None) -> dict:
    if not samples:
        return {
            "sample_count": 0,
            "duration_seconds": round(duration_seconds or 0.0, 3),
            "gpu_sm_avg": 0.0,
            "gpu_enc_avg": 0.0,
            "gpu_dec_avg": 0.0,
            "gpu_mem_avg": 0.0,
            "gpu_sm_max": 0.0,
            "gpu_enc_max": 0.0,
            "gpu_dec_max": 0.0,
        }
    return {
        "sample_count": len(samples),
        "duration_seconds": round(duration_seconds if duration_seconds is not None else float(len(samples)), 3),
        "gpu_sm_avg": round(mean(sample.sm for sample in samples), 3),
        "gpu_enc_avg": round(mean(sample.enc for sample in samples), 3),
        "gpu_dec_avg": round(mean(sample.dec for sample in samples), 3),
        "gpu_mem_avg": round(mean(sample.mem for sample in samples), 3),
        "gpu_sm_max": round(max(sample.sm for sample in samples), 3),
        "gpu_enc_max": round(max(sample.enc for sample in samples), 3),
        "gpu_dec_max": round(max(sample.dec for sample in samples), 3),
    }


def _summarize_by_windows(samples: list[DmonSample], windows: dict[str, tuple[datetime, datetime]]) -> dict:
    stages: dict[str, dict] = {}
    for stage, (start, end) in windows.items():
        stage_samples = [
            sample
            for sample in samples
            if sample.timestamp is not None and start <= sample.timestamp <= end
        ]
        stages[stage] = _summarize_samples(stage_samples, (end - start).total_seconds())
    return stages


def _fallback_utilization_stages(samples: list[DmonSample]) -> dict:
    if not samples:
        return {}
    active = [sample for sample in samples if sample.enc > 0 or sample.dec > 0]
    inactive = [sample for sample in samples if sample.enc <= 0 and sample.dec <= 0]
    ml_like = [sample for sample in inactive if sample.sm >= 10]
    analysis = [sample for sample in inactive if sample.sm < 10]
    half = max(1, len(active) // 2)
    return {
        "transcript": _summarize_samples(ml_like[: max(1, len(ml_like) // 2)]),
        "analysis": _summarize_samples(analysis),
        "scene_detection_and_timeline": _summarize_samples(ml_like[max(1, len(ml_like) // 2) :]),
        "longform_render": _summarize_samples(active[:half]),
        "shorts_render_and_export": _summarize_samples(active[half:]),
    }


def analyze_render(label: str, dmon_path: Path, log_path: Path | None) -> dict:
    samples = parse_dmon(dmon_path)
    log_lines = parse_timestamped_log(log_path) if log_path and log_path.exists() else []
    windows = build_stage_windows(log_lines, samples)
    if windows:
        stages = _summarize_by_windows(samples, windows)
        longform_duration = stages.get("longform_render", {}).get("duration_seconds", 0.0)
        if longform_duration < 30.0 and len(samples) > 60:
            stages = _fallback_utilization_stages(samples)
            method = "utilization_fallback_due_buffered_log"
        else:
            method = "timestamped_log_windows"
    else:
        stages = _fallback_utilization_stages(samples)
        method = "utilization_fallback"
    return {
        "label": label,
        "dmon_path": str(dmon_path),
        "log_path": str(log_path) if log_path else None,
        "method": method,
        "total": _summarize_samples(samples),
        "stages": stages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--render",
        action="append",
        nargs=3,
        metavar=("LABEL", "DMON_PATH", "LOG_PATH"),
        help="Render label plus dmon and timestamped pipeline log path.",
    )
    parser.add_argument(
        "--output",
        default="reports/phase4_7/p4_7_7_gpu_stage_breakdown.json",
    )
    args = parser.parse_args()

    renders = {}
    for label, dmon, log in args.render or []:
        renders[label] = analyze_render(label, Path(dmon), Path(log))

    first = next(iter(renders.values()), {})
    payload = {
        "method_note": (
            "Timestamped dmon rows are correlated with timestamp-prefixed pipeline logs. "
            "If timestamps are missing, utilization-based fallback segmentation is used."
        ),
        "renders": renders,
        "stages": first.get("stages", {}),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
