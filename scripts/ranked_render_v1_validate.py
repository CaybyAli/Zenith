from __future__ import annotations

import json
import math
import re
import subprocess
import ast
from pathlib import Path
from typing import Any

PLAN = Path("reports/highlight_ranking_mandatory_tighten/highlight_ranking_mandatory_tighten_final_editorial_plan.json")
AUDIT = Path("reports/highlight_ranking_mandatory_tighten/highlight_ranking_mandatory_tighten_audit.json")
VIDEO = Path("reports/ranked_render/ranked_cut_v1.mp4")
REPORT = Path("reports/ranked_render/ranked_cut_v1_validation_report.txt")
LOG = Path("reports/ranked_render/ranked_cut_v1_render_log.txt")
GPU = Path("reports/ranked_render/ranked_cut_v1_gpu_monitor.csv")

TARGETS = [
    ("Start-owner-onset", 9.82, 30.0),
    ("Runde-1-Kampf", 142.0, 246.0),
    ("Runde-1-Ende-getrimmt", 246.0, 259.802),
    ("Runden-Uebergang-entfernt", 259.802, 285.734),
    ("Runde-2-Start-Sprechonset", 285.734, 300.0),
    ("Runde-2-NEE-wenn-dann-hier", 721.641, 733.564),
    ("Tod-Payoff gelockt", 1756.0, 1810.817),
    ("Tod-Payoff", 1792.0, 1810.417),
    ("Late-Lobby gehalten #1", 918.596, 967.612),
    ("Late-Lobby gehalten #2", 1622.372, 1648.0),
]

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        x = float(str(value).strip())
    except Exception:
        return default
    return x if math.isfinite(x) else default

def fmt(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m:02d}:{s:06.3f}"

def find_segments(raw: Any) -> list[dict[str, Any]]:
    keys = ("timeline_segments", "segments", "selected_segments", "final_segments", "clips", "timeline")
    def looks(v: Any) -> bool:
        return isinstance(v, list) and v and isinstance(v[0], dict) and (
            any(k in v[0] for k in ("start_seconds", "start", "start_time"))
            and any(k in v[0] for k in ("end_seconds", "end", "end_time"))
        )
    if isinstance(raw, dict):
        for key in keys:
            if looks(raw.get(key)):
                return raw[key]
        for v in raw.values():
            if looks(v):
                return v
        for v in raw.values():
            if isinstance(v, dict):
                try:
                    return find_segments(v)
                except Exception:
                    pass
    raise RuntimeError("Keine Segmentliste gefunden")

def se(seg: dict[str, Any]) -> tuple[float, float]:
    return (
        safe_float(seg.get("start_seconds", seg.get("start", seg.get("start_time")))),
        safe_float(seg.get("end_seconds", seg.get("end", seg.get("end_time")))),
    )

def ffprobe(path: Path) -> dict[str, Any]:
    cmd = [
        "D:\\Tools\\ffmpeg\\bin\\ffprobe.exe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(p.stderr)
    return json.loads(p.stdout)

def map_time(segments: list[dict[str, Any]], a: float, b: float) -> list[str]:
    out = []
    cursor = 0.0
    for idx, seg in enumerate(segments, 1):
        s, e = se(seg)
        d = max(0.0, e - s)
        ov_s = max(s, a)
        ov_e = min(e, b)
        if ov_e > ov_s:
            r_s = cursor + (ov_s - s)
            r_e = cursor + (ov_e - s)
            out.append(f"segment#{idx} source={ov_s:.3f}->{ov_e:.3f} render={fmt(r_s)}->{fmt(r_e)}")
        cursor += d
    return out

def parse_render_log_segment_total(text: str) -> int:
    matches = re.findall(r"SEGMENT\s+\d+\s*/\s*(\d+)", text, flags=re.IGNORECASE)
    if matches:
        return int(matches[-1])

    matches = re.findall(r"\bsegments\s*=\s*(\d+)\b", text, flags=re.IGNORECASE)
    if matches:
        return int(matches[-1])

    matches = re.findall(r'"segment_count"\s*:\s*(\d+)', text, flags=re.IGNORECASE)
    return int(matches[-1]) if matches else -1


def parse_render_seconds_from_log(text: str) -> str:
    matches = re.findall(r"\brender_seconds\s*=\s*([0-9]+(?:[\.,][0-9]+)?)\b", text, flags=re.IGNORECASE)
    return matches[-1].replace(",", ".") if matches else "MISSING"


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def parse_gpu_summary_from_log(text: str) -> dict[str, Any] | None:
    matches = re.findall(r"\bgpu_summary\s*=\s*(\{.*?\})(?:\r?\n|$)", text, flags=re.IGNORECASE)
    if not matches:
        return None

    raw = matches[-1].strip()
    try:
        parsed = json.loads(raw)
    except Exception:
        try:
            parsed = ast.literal_eval(raw)
        except Exception:
            return None

    return parsed if isinstance(parsed, dict) else None


def parse_gpu_monitor_csv(text: str) -> dict[str, Any]:
    rows = []
    for line in text.splitlines()[1:]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        try:
            rows.append((float(parts[1]), float(parts[2]), float(parts[3])))
        except Exception:
            pass
    if not rows:
        return {"exists": True, "rows": 0}
    return {
        "exists": True,
        "rows": len(rows),
        "gpu_avg": round(sum(x[0] for x in rows) / len(rows), 3),
        "gpu_max": round(max(x[0] for x in rows), 3),
        "enc_avg": round(sum(x[1] for x in rows) / len(rows), 3),
        "enc_max": round(max(x[1] for x in rows), 3),
        "power_avg_w": round(sum(x[2] for x in rows) / len(rows), 3),
        "power_max_w": round(max(x[2] for x in rows), 3),
    }


def log_segment_total(log_path: Path = LOG) -> int:
    if not log_path.exists():
        return -1
    return parse_render_log_segment_total(read_text_auto(log_path))

def render_seconds(log_path: Path = LOG) -> str:
    if not log_path.exists():
        return "MISSING"
    return parse_render_seconds_from_log(read_text_auto(log_path))

def gpu_summary(gpu_path: Path = GPU, log_path: Path = LOG) -> dict[str, Any]:
    if gpu_path.exists():
        return parse_gpu_monitor_csv(read_text_auto(gpu_path))
    if log_path.exists():
        parsed = parse_gpu_summary_from_log(read_text_auto(log_path))
        if parsed is not None:
            parsed.setdefault("exists", True)
            return parsed
    return {"exists": False}


def build_validation_report(
    *,
    plan_path: Path = PLAN,
    audit_path: Path = AUDIT,
    video_path: Path = VIDEO,
    report_path: Path = REPORT,
    log_path: Path = LOG,
    gpu_path: Path = GPU,
) -> str:
    plan = read_json(plan_path)
    _audit = read_json(audit_path) if audit_path.exists() else {}
    del _audit

    segments = find_segments(plan)
    expected_duration = round(sum(max(0.0, se(seg)[1] - se(seg)[0]) for seg in segments), 3)

    probe = ffprobe(video_path)
    streams = probe["streams"]
    v = [s for s in streams if s.get("codec_type") == "video"]
    a = [s for s in streams if s.get("codec_type") == "audio"]
    duration = round(safe_float(probe["format"].get("duration")), 3)
    width = v[0].get("width") if v else None
    height = v[0].get("height") if v else None

    expected_segments = len(segments)
    actual_segments = log_segment_total(log_path)
    segment_exact_match = expected_segments == actual_segments
    delta = round(abs(duration - expected_duration), 3)

    lines = []
    lines.append("PROJECT ZENITH - RANKED CUT VALIDATION")
    lines.append("")
    lines.append(f"input_plan={plan_path}")
    lines.append(f"output_video={video_path}")
    lines.append(f"exists={video_path.exists()}")
    lines.append("")
    lines.append("FFPROBE")
    lines.append(f"duration_seconds={duration}")
    lines.append(f"expected_duration_seconds={expected_duration}")
    lines.append(f"duration_delta_seconds={delta}")
    lines.append(f"resolution={width}x{height}")
    lines.append(f"audio_stream_count={len(a)}")
    lines.append("")
    lines.append("SEGMENT CHECK")
    lines.append(f"expected_kept_segments={expected_segments}")
    lines.append(f"render_log_segment_total={actual_segments}")
    lines.append(f"segment_exact_match={segment_exact_match}")
    lines.append(f"anti_overcut=0")
    lines.append("")
    lines.append("PERFORMANCE")
    lines.append(f"render_seconds={render_seconds(log_path)}")
    lines.append(f"gpu_summary={gpu_summary(gpu_path, log_path)}")
    lines.append("")
    lines.append("STELLEN-MAPPING AUF RENDER-ZEIT")
    for name, s, e in TARGETS:
        lines.append(f"- {name} source={s}->{e}")
        mapped = map_time(segments, s, e)
        if not mapped:
            lines.append("  - NICHT IM RENDER GEFUNDEN")
        else:
            for m in mapped:
                lines.append(f"  - {m}")

    overall = (
        video_path.exists()
        and delta <= 1.0
        and width == 1920
        and height == 1080
        and len(a) >= 1
        and segment_exact_match
        and render_seconds(log_path) != "MISSING"
    )

    lines.append("")
    lines.append(f"overall_pass={overall}")
    lines.append("STOPP: Kein Commit.")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(lines)


if __name__ == "__main__":
    print(build_validation_report())
