from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(".")
PAIRS_DIR = ROOT / "learning_corpus" / "pairs"
REPORT_DIR = ROOT / "reports" / "phase4_8"
REPORT_PATH = REPORT_DIR / "P4_8_A4B_SPEAKER_TRACK_FIX_REPORT.json"

TRACK_MAPPING = {
    0: "ali",
    1: "friend",
    2: "game",
}

MANUAL_MAPPING_REFERENCE = {
    "reference_pair": "pair_007",
    "verified_by": "manual_listening",
    "mapping": {
        "a0": "ali_voice",
        "a1": "discord_friends",
        "a2": "game_sound",
    },
    "note": "Manual listening proof: a0=Ali mic, a1=Discord/friends, a2=game sound.",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ffmpeg_path() -> str:
    candidate = Path(r"D:\Tools\ffmpeg\bin\ffmpeg.exe")
    return str(candidate) if candidate.exists() else "ffmpeg"


def ffprobe_path() -> str:
    candidate = Path(r"D:\Tools\ffmpeg\bin\ffprobe.exe")
    return str(candidate) if candidate.exists() else "ffprobe"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp" + path.suffix)
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(path)


def probe_raw(raw_path: Path) -> dict[str, Any]:
    cmd = [
        ffprobe_path(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(raw_path),
    ]
    payload = json.loads(subprocess.check_output(cmd, text=True, encoding="utf-8", errors="replace"))
    duration = float(payload.get("format", {}).get("duration", 0.0) or 0.0)
    audio_streams = [s for s in payload.get("streams", []) if s.get("codec_type") == "audio"]
    return {
        "duration_seconds": duration,
        "audio_stream_count": len(audio_streams),
        "audio_streams": audio_streams,
    }


def analyze_track_activity(raw_path: Path, track_index: int, duration_seconds: float) -> dict[str, Any]:
    cmd = [
        ffmpeg_path(),
        "-hide_banner",
        "-nostats",
        "-i", str(raw_path),
        "-map", f"0:a:{track_index}",
        "-vn",
        "-af", "silencedetect=noise=-38dB:d=0.30",
        "-f", "null",
        "-",
    ]

    started = time.monotonic()
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1200,
        check=False,
    )

    stderr = completed.stderr or ""
    silence_durations = [float(x) for x in re.findall(r"silence_duration:\s*([0-9.]+)", stderr)]
    silence_seconds = sum(silence_durations)

    active_seconds = max(0.0, float(duration_seconds) - silence_seconds)
    active_ratio = active_seconds / duration_seconds if duration_seconds > 0 else 0.0

    return {
        "track_index": track_index,
        "role": TRACK_MAPPING.get(track_index, "unknown"),
        "returncode": completed.returncode,
        "duration_seconds": round(duration_seconds, 3),
        "silence_seconds": round(silence_seconds, 3),
        "active_seconds": round(active_seconds, 3),
        "active_ratio": round(active_ratio, 6),
        "silence_event_count": len(silence_durations),
        "duration_runtime_seconds": round(time.monotonic() - started, 3),
        "ok": completed.returncode == 0,
        "stderr_tail": stderr[-1200:],
    }


def build_distribution(activity: dict[str, dict[str, Any]]) -> dict[str, float]:
    ali_active = float(activity.get("ali", {}).get("active_seconds", 0.0) or 0.0)
    friend_active = float(activity.get("friend", {}).get("active_seconds", 0.0) or 0.0)

    total = ali_active + friend_active
    if total <= 0.0:
        return {"ali": 0.0, "friend": 0.0, "unknown": 100.0}

    return {
        "ali": round((ali_active / total) * 100.0, 3),
        "friend": round((friend_active / total) * 100.0, 3),
        "unknown": 0.0,
    }


def patch_pair(pair_name: str, *, apply: bool) -> dict[str, Any]:
    pair_dir = PAIRS_DIR / pair_name
    raw_path = pair_dir / "raw.mp4"
    fp_path = pair_dir / "style_fingerprint.json"

    if not raw_path.exists():
        raise FileNotFoundError(f"missing raw.mp4: {raw_path}")
    if not fp_path.exists():
        raise FileNotFoundError(f"missing style_fingerprint.json: {fp_path}")

    probe = probe_raw(raw_path)
    if int(probe["audio_stream_count"]) < 3:
        raise RuntimeError(f"{pair_name} has fewer than 3 audio streams: {probe['audio_stream_count']}")

    duration_seconds = float(probe["duration_seconds"])
    if duration_seconds <= 0.0:
        raise RuntimeError(f"{pair_name} raw.mp4 has invalid duration")

    per_track = {}
    by_role = {}

    for track_index, role in TRACK_MAPPING.items():
        details = analyze_track_activity(raw_path, track_index, duration_seconds)
        per_track[f"a{track_index}"] = details
        if not details["ok"]:
            raise RuntimeError(f"{pair_name} track a{track_index} analysis failed")
        by_role[role] = details

    distribution = build_distribution(by_role)

    data = read_json(fp_path)
    old_distribution = data.get("speaker_distribution", {})

    data["speaker_distribution"] = {
        **distribution,
        "status": "verified",
        "source": "manual_track_mapping_raw_audio_activity",
        "confidence": 0.85,
        "method": "p4_8_a4b_raw_multitrack_silencedetect_v1",
        "raw_source_path": str(raw_path),
        "track_count": int(probe["audio_stream_count"]),
        "track_mapping": {
            "a0": "ali",
            "a1": "friend",
            "a2": "game",
        },
        "activity_seconds": {
            "ali": by_role["ali"]["active_seconds"],
            "friend": by_role["friend"]["active_seconds"],
            "game": by_role["game"]["active_seconds"],
        },
        "activity_ratio": {
            "ali": by_role["ali"]["active_ratio"],
            "friend": by_role["friend"]["active_ratio"],
            "game": by_role["game"]["active_ratio"],
        },
        "distribution_basis": "ali_friend_active_seconds_only_game_track_excluded",
        "manual_mapping_reference": MANUAL_MAPPING_REFERENCE,
        "previous_distribution": old_distribution,
    }

    data["speaker_distribution_source"] = "track_mapping"
    data["speaker_distribution_source_path"] = str(raw_path)
    data["p4_8_a4b_speaker_track_fix_timestamp_utc"] = now_utc()
    data["p4_8_a4b_speaker_track_fix_version"] = "p4_8_a4b_v1"
    data["p4_8_a4b_speaker_track_evidence"] = {
        "probe": {
            "raw_path": str(raw_path),
            "duration_seconds": round(duration_seconds, 3),
            "audio_stream_count": int(probe["audio_stream_count"]),
        },
        "per_track": per_track,
        "manual_mapping_reference": MANUAL_MAPPING_REFERENCE,
    }

    if apply:
        write_json(fp_path, data)

    return {
        "pair": pair_name,
        "apply": apply,
        "fingerprint_path": str(fp_path),
        "raw_path": str(raw_path),
        "audio_stream_count": int(probe["audio_stream_count"]),
        "speaker_distribution": data["speaker_distribution"],
        "speaker_distribution_source": data["speaker_distribution_source"],
        "old_distribution": old_distribution,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    result = patch_pair(args.pair, apply=args.apply)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(REPORT_PATH, {
        "status": "ok",
        "timestamp_utc": now_utc(),
        "result": result,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
