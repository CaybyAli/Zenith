from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(".")
PAIR_ROOT = ROOT / "learning_corpus" / "pairs"
REPORT_DIR = ROOT / "reports" / "phase4_8" / "preflight"
STOPP_PATH = ROOT / "reports" / "phase4_8" / "STOPP_PREFLIGHT.md"

EXPECTED_TRACKS = {
    **{f"pair_{i:03d}": 4 for i in range(1, 6)},
    **{f"pair_{i:03d}": 3 for i in range(6, 8)},
    **{f"pair_{i:03d}": 4 for i in range(8, 21)},
}
EXPECTED_FINGERPRINTS = {
    "learning_corpus/pairs": 0,
    "learning_corpus/top_solo": 30,
    "learning_corpus/vlogs": 3,
}


def ffprobe_audio_streams(raw_path: Path) -> tuple[list[dict], str | None]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_type,codec_name,channels",
        "-of",
        "json",
        str(raw_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return [], result.stderr.strip() or f"ffprobe exited {result.returncode}"
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return [], f"invalid ffprobe json: {exc}"
    streams = [
        stream
        for stream in data.get("streams", [])
        if stream.get("codec_type") == "audio"
    ]
    return streams, None


def count_fingerprints(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.rglob("style_fingerprint.json"))


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    pair_results: dict[str, dict] = {}
    pair_dirs = sorted(p for p in PAIR_ROOT.iterdir() if p.is_dir()) if PAIR_ROOT.exists() else []

    for pair_dir in pair_dirs:
        raw = pair_dir / "raw.mp4"
        final = pair_dir / "final.mp4"
        meta = pair_dir / "meta.json"
        audio_streams: list[dict] = []
        ffprobe_error = None
        if raw.exists():
            audio_streams, ffprobe_error = ffprobe_audio_streams(raw)

        pair_results[pair_dir.name] = {
            "has_raw": raw.exists(),
            "has_final": final.exists(),
            "has_meta": meta.exists(),
            "raw_size_mb": round(raw.stat().st_size / (1024 * 1024), 2) if raw.exists() else 0,
            "final_size_mb": round(final.stat().st_size / (1024 * 1024), 2) if final.exists() else 0,
            "audio_tracks": len(audio_streams),
            "audio_codecs": [stream.get("codec_name") for stream in audio_streams],
            "audio_channels": [stream.get("channels") for stream in audio_streams],
            "audio_stream_indices": [stream.get("index") for stream in audio_streams],
            "ffprobe_error": ffprobe_error,
        }

    fingerprint_counts = {
        rel: count_fingerprints(ROOT / rel)
        for rel in EXPECTED_FINGERPRINTS
    }

    multi = sum(1 for info in pair_results.values() if info["audio_tracks"] >= 2)
    single = sum(1 for info in pair_results.values() if info["audio_tracks"] == 1)
    no_audio = sum(1 for info in pair_results.values() if info["audio_tracks"] == 0)

    mismatches: list[str] = []
    expected_pair_names = sorted(EXPECTED_TRACKS)
    actual_pair_names = sorted(pair_results)
    if actual_pair_names != expected_pair_names:
        missing = sorted(set(expected_pair_names) - set(actual_pair_names))
        extra = sorted(set(actual_pair_names) - set(expected_pair_names))
        mismatches.append(
            f"Pair set mismatch: expected {len(expected_pair_names)} pairs, "
            f"found {len(actual_pair_names)}; missing={missing}; extra={extra}"
        )

    for pair_name, expected_tracks in EXPECTED_TRACKS.items():
        info = pair_results.get(pair_name)
        if info is None:
            continue
        if not info["has_raw"] or not info["has_final"] or not info["has_meta"]:
            mismatches.append(
                f"{pair_name}: file presence mismatch "
                f"raw={info['has_raw']} final={info['has_final']} meta={info['has_meta']}"
            )
        if info["audio_tracks"] != expected_tracks:
            mismatches.append(
                f"{pair_name}: expected {expected_tracks} audio tracks, "
                f"found {info['audio_tracks']}"
            )
        if info.get("ffprobe_error"):
            mismatches.append(f"{pair_name}: ffprobe error: {info['ffprobe_error']}")

    for rel, expected in EXPECTED_FINGERPRINTS.items():
        actual = fingerprint_counts.get(rel, 0)
        if actual != expected:
            mismatches.append(
                f"{rel}: expected {expected} style_fingerprint.json files, found {actual}"
            )

    summary = {
        "pair_count": len(pair_results),
        "multi_track_pairs": multi,
        "single_track_pairs": single,
        "no_audio_pairs": no_audio,
        "fingerprint_counts": fingerprint_counts,
        "mismatches": mismatches,
    }

    audit = {
        "summary": summary,
        "pairs": pair_results,
    }
    (REPORT_DIR / "audio_track_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    lines = [
        "# Phase 4.8 A1 Preflight Audio Track Audit",
        "",
        f"Total Pairs: {len(pair_results)}",
        f"Multi-Track (>= 2 audio): {multi}",
        f"Single-Track (1 audio): {single}",
        f"No-Audio: {no_audio}",
        "",
        "## Fingerprints",
    ]
    lines.extend(
        f"- {rel}: {fingerprint_counts.get(rel, 0)}"
        for rel in sorted(fingerprint_counts)
    )
    lines.extend(["", "## Pairs", ""])
    lines.append(
        "| Pair | raw.mp4 | final.mp4 | meta.json | Audio tracks | Codecs | Channels |"
    )
    lines.append("|---|---:|---:|---:|---:|---|---|")
    for pair_name in sorted(pair_results):
        info = pair_results[pair_name]
        lines.append(
            f"| {pair_name} | {info['has_raw']} | {info['has_final']} | "
            f"{info['has_meta']} | {info['audio_tracks']} | "
            f"{', '.join(str(x) for x in info['audio_codecs'])} | "
            f"{', '.join(str(x) for x in info['audio_channels'])} |"
        )
    lines.extend(["", "## Result", ""])
    if mismatches:
        lines.append("STOPP_PREFLIGHT")
        lines.extend(f"- {item}" for item in mismatches)
    else:
        lines.append("PASS: local corpus state matches the user-reported preflight numbers.")
    (REPORT_DIR / "audio_track_audit.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if mismatches:
        STOPP_PATH.write_text(
            "\n".join(
                [
                    "# STOPP_PREFLIGHT",
                    "",
                    "P4.8 was stopped during A1 because the local preflight numbers "
                    "did not match the user-reported expected state.",
                    "",
                    "## Mismatches",
                    "",
                    *[f"- {item}" for item in mismatches],
                    "",
                    "No further P4.8 subphases were started.",
                    "",
                    f"Detailed audit: {REPORT_DIR / 'audio_track_audit.json'}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        print("STOPP_PREFLIGHT")
        for mismatch in mismatches:
            print(f"- {mismatch}")
        return 2

    print(f"Total Pairs: {len(pair_results)}")
    print(f"Multi-Track (>= 2 audio): {multi}")
    print(f"Single-Track (1 audio): {single}")
    print(f"No-Audio: {no_audio}")
    for rel in sorted(fingerprint_counts):
        print(f"{rel}: {fingerprint_counts[rel]} style_fingerprint.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
