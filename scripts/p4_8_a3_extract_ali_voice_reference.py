from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(".")
AUDIT_PATH = ROOT / "reports" / "phase4_8" / "preflight" / "audio_track_audit.json"
REPORT_PATH = ROOT / "reports" / "phase4_8" / "p4_8_a3_voice_reference_audit.json"
OUTPUT = ROOT / "data" / "voice_references" / "ali_voice_reference.wav"


def load_pair_audit() -> dict[str, dict]:
    data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    return data.get("pairs", data)


def main() -> int:
    audit = load_pair_audit()
    target_pair = next(
        (
            pair_name
            for pair_name, info in sorted(audit.items())
            if int(info.get("audio_tracks", 0) or 0) >= 2
        ),
        None,
    )
    if target_pair is None:
        print("No multi-track pair found")
        return 1

    raw = ROOT / "learning_corpus" / "pairs" / target_pair / "raw.mp4"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        "60",
        "-t",
        "10",
        "-i",
        str(raw),
        "-map",
        "0:a:1",
        "-ac",
        "1",
        "-ar",
        "16000",
        str(OUTPUT),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)

    size_bytes = OUTPUT.stat().st_size if OUTPUT.exists() else 0
    result = {
        "source_pair": target_pair,
        "source_path": str(raw),
        "output_path": str(OUTPUT),
        "audio_map": "0:a:1",
        "start_seconds": 60,
        "duration_seconds": 10,
        "returncode": completed.returncode,
        "size_bytes": size_bytes,
        "meets_min_size": size_bytes > 100_000,
        "stderr": (completed.stderr or "")[-2000:],
    }
    REPORT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if completed.returncode == 0 and result["meets_min_size"]:
        print(f"Created {OUTPUT} ({size_bytes} bytes)")
        return 0

    print(f"Failed to create valid reference sample, size={size_bytes}")
    if completed.stderr:
        print(completed.stderr[-1000:])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
