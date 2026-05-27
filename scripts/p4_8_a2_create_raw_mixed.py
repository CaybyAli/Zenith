from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(".")
AUDIT_PATH = ROOT / "reports" / "phase4_8" / "preflight" / "audio_track_audit.json"
REPORT_PATH = ROOT / "reports" / "phase4_8" / "p4_8_a2_mixed_audio_audit.json"
STOPP_PATH = ROOT / "reports" / "phase4_8" / "STOPP_A2_MIXED_AUDIO.md"


def load_audit() -> dict[str, dict]:
    data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if "pairs" in data:
        return data["pairs"]
    return data


def run_ffmpeg(pair_name: str, raw: Path, mixed: Path, audio_tracks: int) -> tuple[bool, str]:
    filters = []
    for i in range(audio_tracks):
        volume = 1.0 if i == 0 else 0.7
        filters.append(f"[0:a:{i}]volume={volume}[a{i}]")
    audio_inputs = "".join(f"[a{i}]" for i in range(audio_tracks))
    filter_complex = ";".join(filters + [f"{audio_inputs}amix=inputs={audio_tracks}:duration=longest[aout]"])

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(raw),
        "-filter_complex",
        filter_complex,
        "-map",
        "0:v:0",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ac",
        "2",
        "-movflags",
        "+faststart",
        str(mixed),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and mixed.exists() and mixed.stat().st_size > 0:
        return True, ""
    if mixed.exists() and mixed.stat().st_size == 0:
        mixed.unlink()
    return False, (result.stderr or result.stdout or f"ffmpeg exited {result.returncode}")[:2000]


def main() -> int:
    audit = load_audit()
    created: list[str] = []
    already_exists: list[str] = []
    skipped: list[dict] = []
    failures: list[dict] = []

    for pair_name in sorted(audit):
        info = audit[pair_name]
        audio_tracks = int(info.get("audio_tracks", 0) or 0)
        pair_dir = ROOT / "learning_corpus" / "pairs" / pair_name
        raw = pair_dir / "raw.mp4"
        mixed = pair_dir / "raw_mixed_audio.mp4"

        if audio_tracks < 2:
            skipped.append({"pair": pair_name, "reason": "not multi-track"})
            continue
        if not raw.exists():
            failures.append({"pair": pair_name, "reason": "missing raw.mp4"})
            continue
        if mixed.exists() and mixed.stat().st_size > 0:
            already_exists.append(pair_name)
            continue

        print(f"Creating raw_mixed_audio for {pair_name} ({audio_tracks} tracks)...", flush=True)
        ok, error = run_ffmpeg(pair_name, raw, mixed, audio_tracks)
        if ok:
            created.append(pair_name)
        else:
            failures.append({"pair": pair_name, "reason": error})

    multi_track_pairs = [
        pair_name
        for pair_name, info in audit.items()
        if int(info.get("audio_tracks", 0) or 0) >= 2
    ]
    missing_outputs = []
    for pair_name in multi_track_pairs:
        mixed = ROOT / "learning_corpus" / "pairs" / pair_name / "raw_mixed_audio.mp4"
        if not mixed.exists() or mixed.stat().st_size == 0:
            missing_outputs.append(pair_name)

    result = {
        "multi_track_pairs": len(multi_track_pairs),
        "created": created,
        "already_exists": already_exists,
        "skipped": skipped,
        "failures": failures,
        "missing_outputs": missing_outputs,
        "success": not failures and not missing_outputs,
    }
    REPORT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    if len(failures) > len(multi_track_pairs) / 2:
        STOPP_PATH.write_text(
            "\n".join(
                [
                    "# STOPP_A2_MIXED_AUDIO",
                    "",
                    "More than 50% of multi-track pairs failed during raw_mixed_audio generation.",
                    "",
                    "## Failures",
                    "",
                    *[f"- {item['pair']}: {item['reason']}" for item in failures],
                    "",
                    f"Detailed audit: {REPORT_PATH}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        print("STOPP_A2_MIXED_AUDIO")
        return 2

    print(f"Created: {len(created)}")
    print(f"Already exists: {len(already_exists)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Failures: {len(failures)}")
    print(f"Missing outputs: {len(missing_outputs)}")
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
