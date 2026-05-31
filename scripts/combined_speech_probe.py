from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.combined_speech import (
    build_combined_silence_gaps,
    build_combined_speech_summary,
    combine_speech_regions,
    find_friend_speaks_owner_silent_examples,
)
from core.real_vad_validation import coverage_seconds

from speech_1_fix_2_real_vad_probe import (
    _extract_mic_wav,
    _media_duration_from_speech_report,
    _probe_duration,
    _run_silero_vad,
)


OWNER_PROTECTION_WINDOWS = [
    {
        "name": "busfahrer_speech_around_287",
        "start_seconds": 284.0,
        "end_seconds": 292.0,
        "min_speech_overlap_seconds": 0.5,
    },
    {
        "name": "death_talk_1786_to_1810",
        "start_seconds": 1786.0,
        "end_seconds": 1810.5,
        "min_speech_overlap_seconds": 3.0,
    },
]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _validate_owner_protection(
    *,
    combined_regions: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    for spec in OWNER_PROTECTION_WINDOWS:
        start = float(spec["start_seconds"])
        end = float(spec["end_seconds"])
        minimum = float(spec["min_speech_overlap_seconds"])

        overlap = coverage_seconds(
            combined_regions,
            start_seconds=start,
            end_seconds=end,
        )

        checks.append({
            "name": spec["name"],
            "range_seconds": [start, end],
            "combined_speech_overlap_seconds": overlap,
            "min_required_seconds": minimum,
            "status": "PASS" if overlap >= minimum else "FAIL",
        })

    return checks


def _write_report(
    *,
    report_path: Path,
    video_path: Path,
    owner_track: int,
    friend_track: int,
    threshold: float,
    media_duration_seconds: float,
    owner_metadata: dict[str, Any],
    friend_metadata: dict[str, Any],
    owner_regions_path: Path,
    friend_regions_path: Path,
    combined_regions_path: Path,
    combined_silence_path: Path,
    summary: dict[str, Any],
    owner_checks: list[dict[str, Any]],
    friend_only_examples: list[dict[str, Any]],
) -> None:
    lines: list[str] = []

    lines.append('PROJECT ZENITH - COMBINED-SPEECH REPORT')
    lines.append("")
    lines.append(f"video={video_path}")
    lines.append(f"owner_track={owner_track}")
    lines.append(f"friend_track={friend_track}")
    lines.append(f"silero_threshold={threshold}")
    lines.append(f"media_duration_seconds={round(media_duration_seconds, 3)}")
    lines.append("")
    lines.append("ENGINE")
    lines.append(f"- owner_engine={owner_metadata.get('engine')}")
    lines.append(f"- friend_engine={friend_metadata.get('engine')}")
    lines.append("- energy_fallback_used=False")
    lines.append("- game_track_used=False")
    lines.append("")
    lines.append("OUTPUTS")
    lines.append(f"- owner_speech_regions={owner_regions_path}")
    lines.append(f"- friend_speech_regions={friend_regions_path}")
    lines.append(f"- combined_speech_regions={combined_regions_path}")
    lines.append(f"- combined_silence_gaps={combined_silence_path}")
    lines.append(f"- report={report_path}")
    lines.append("")
    lines.append("SPEECH SHARE COMPARISON")
    lines.append(f"- owner_speech_seconds={summary.get('owner_speech_seconds')}")
    lines.append(f"- friend_speech_seconds={summary.get('friend_speech_seconds')}")
    lines.append(f"- combined_speech_seconds={summary.get('combined_speech_seconds')}")
    lines.append(f"- combined_silence_seconds={summary.get('combined_silence_seconds')}")
    lines.append(f"- owner_speech_share_percent={summary.get('owner_speech_share_percent')}")
    lines.append(f"- friend_speech_share_percent={summary.get('friend_speech_share_percent')}")
    lines.append(f"- combined_speech_share_percent={summary.get('combined_speech_share_percent')}")
    lines.append("")
    lines.append("OWNER PROTECTION CHECKS")
    for check in owner_checks:
        lines.append(
            f"- {check.get('status')} {check.get('name')} "
            f"range={check.get('range_seconds')} "
            f"combined_speech_overlap={check.get('combined_speech_overlap_seconds')} "
            f"min={check.get('min_required_seconds')}"
        )
    lines.append("")
    lines.append("KERN-BEWEIS: FRIEND SPEAKS WHILE OWNER SILENT")
    if not friend_only_examples:
        lines.append("- FAIL: no friend-only speech examples found")
    for index, item in enumerate(friend_only_examples[:5], start=1):
        lines.append(
            f"{index}. {item.get('status')} "
            f"friend_only={item.get('start_seconds')}->{item.get('end_seconds')} "
            f"duration={item.get('duration_seconds')} "
            f"owner_overlap={item.get('owner_overlap_seconds')} "
            f"combined_overlap={item.get('combined_overlap_seconds')} "
            f"reason={item.get('reason')}"
        )
    lines.append("")
    failed_owner = [item for item in owner_checks if item.get("status") != "PASS"]
    failed_friend_examples = [item for item in friend_only_examples[:2] if item.get("status") != "PASS"]
    has_friend_examples = len(friend_only_examples) >= 1

    overall = "PASS" if not failed_owner and has_friend_examples and not failed_friend_examples else "FAIL"

    lines.append("VERDICT")
    lines.append(f"- owner_protection_failed_count={len(failed_owner)}")
    lines.append(f"- friend_only_example_count={len(friend_only_examples)}")
    lines.append(f"- overall_status={overall}")
    if overall == "PASS":
        lines.append("- GO_REASON=combined Owner+Discord speech proves that friend-only speech is no longer treated as silence")
    else:
        lines.append("- NO_GO_REASON=combined speech proof incomplete")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default=r"D:\Zenith\inbox\gaming_main\Fortnite Full Video.mp4")
    parser.add_argument("--owner-track", type=int, default=1)
    parser.add_argument("--friend-track", type=int, default=2)
    parser.add_argument("--speech-report", default="reports/speech_1_transcript/speech_1_report.txt")
    parser.add_argument("--out-dir", default="reports/combined_speech")
    parser.add_argument("--silero-threshold", type=float, default=0.05)
    args = parser.parse_args(argv)

    video_path = Path(args.video)
    speech_report_path = Path(args.speech_report)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"video not found: {video_path}")

    media_duration = _media_duration_from_speech_report(speech_report_path)
    if media_duration is None:
        media_duration = _probe_duration(video_path)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        owner_wav = tmp_dir / "owner_track.wav"
        friend_wav = tmp_dir / "friend_track.wav"

        print("[COMBINED-SPEECH] extracting owner track...")
        _extract_mic_wav(
            video_path=video_path,
            mic_track_1based=args.owner_track,
            sample_rate=16000,
            out_wav=owner_wav,
        )

        print("[COMBINED-SPEECH] extracting friend track...")
        _extract_mic_wav(
            video_path=video_path,
            mic_track_1based=args.friend_track,
            sample_rate=16000,
            out_wav=friend_wav,
        )

        print("[COMBINED-SPEECH] running Silero on owner track...")
        owner_regions, owner_metadata = _run_silero_vad(
            wav_path=owner_wav,
            sample_rate=16000,
            media_duration_seconds=float(media_duration),
            threshold=args.silero_threshold,
        )

        print("[COMBINED-SPEECH] running Silero on friend track...")
        friend_regions, friend_metadata = _run_silero_vad(
            wav_path=friend_wav,
            sample_rate=16000,
            media_duration_seconds=float(media_duration),
            threshold=args.silero_threshold,
        )

    combined_regions = combine_speech_regions(
        owner_regions=owner_regions,
        friend_regions=friend_regions,
    )

    combined_silence_gaps = build_combined_silence_gaps(
        combined_speech_regions=combined_regions,
        media_duration_seconds=float(media_duration),
    )

    summary = build_combined_speech_summary(
        owner_regions=owner_regions,
        friend_regions=friend_regions,
        combined_regions=combined_regions,
        combined_silence_gaps=combined_silence_gaps,
        media_duration_seconds=float(media_duration),
    )

    owner_checks = _validate_owner_protection(
        combined_regions=combined_regions,
    )

    friend_only_examples = find_friend_speaks_owner_silent_examples(
        owner_regions=owner_regions,
        friend_regions=friend_regions,
        combined_regions=combined_regions,
        min_duration_seconds=0.60,
        limit=5,
    )

    owner_regions_path = out_dir / "owner_speech_regions_track_1.json"
    friend_regions_path = out_dir / "friend_speech_regions_track_2.json"
    combined_regions_path = out_dir / "combined_speech_regions.json"
    combined_silence_path = out_dir / "combined_silence_gaps.json"
    summary_path = out_dir / "combined_speech_summary.json"
    friend_examples_path = out_dir / "friend_speaks_owner_silent_examples.json"
    report_path = out_dir / "combined_speech_report.txt"

    _write_json(owner_regions_path, {
        "role": "owner",
        "track": args.owner_track,
        "engine": owner_metadata.get("engine"),
        "threshold": args.silero_threshold,
        "speech_regions": owner_regions,
    })
    _write_json(friend_regions_path, {
        "role": "friend",
        "track": args.friend_track,
        "engine": friend_metadata.get("engine"),
        "threshold": args.silero_threshold,
        "speech_regions": friend_regions,
    })
    _write_json(combined_regions_path, {
        "source": "owner_or_friend_speech_union",
        "owner_track": args.owner_track,
        "friend_track": args.friend_track,
        "threshold": args.silero_threshold,
        "speech_regions": combined_regions,
    })
    _write_json(combined_silence_path, {
        "source": "both_owner_and_friend_silent",
        "owner_track": args.owner_track,
        "friend_track": args.friend_track,
        "threshold": args.silero_threshold,
        "silence_gaps": combined_silence_gaps,
    })
    _write_json(summary_path, summary)
    _write_json(friend_examples_path, {
        "examples": friend_only_examples,
    })

    _write_report(
        report_path=report_path,
        video_path=video_path,
        owner_track=args.owner_track,
        friend_track=args.friend_track,
        threshold=args.silero_threshold,
        media_duration_seconds=float(media_duration),
        owner_metadata=owner_metadata,
        friend_metadata=friend_metadata,
        owner_regions_path=owner_regions_path,
        friend_regions_path=friend_regions_path,
        combined_regions_path=combined_regions_path,
        combined_silence_path=combined_silence_path,
        summary=summary,
        owner_checks=owner_checks,
        friend_only_examples=friend_only_examples,
    )

    failed_owner = [item for item in owner_checks if item.get("status") != "PASS"]
    failed_friend = [item for item in friend_only_examples[:2] if item.get("status") != "PASS"]
    overall = "PASS" if not failed_owner and friend_only_examples and not failed_friend else "FAIL"

    print("PROJECT ZENITH - COMBINED-SPEECH")
    print(f"owner_track={args.owner_track}")
    print(f"friend_track={args.friend_track}")
    print(f"engine_owner={owner_metadata.get('engine')}")
    print(f"engine_friend={friend_metadata.get('engine')}")
    print("energy_fallback_used=False")
    print(f"owner_speech_share_percent={summary.get('owner_speech_share_percent')}")
    print(f"friend_speech_share_percent={summary.get('friend_speech_share_percent')}")
    print(f"combined_speech_share_percent={summary.get('combined_speech_share_percent')}")
    print(f"friend_only_example_count={len(friend_only_examples)}")
    print(f"owner_protection_failed_count={len(failed_owner)}")
    print(f"overall_status={overall}")
    print(f"combined_speech_regions={combined_regions_path}")
    print(f"combined_silence_gaps={combined_silence_path}")
    print(f"report={report_path}")

    for item in friend_only_examples[:3]:
        print(
            f"FRIEND_ONLY {item.get('status')} "
            f"{item.get('start_seconds')}->{item.get('end_seconds')} "
            f"duration={item.get('duration_seconds')} "
            f"owner_overlap={item.get('owner_overlap_seconds')} "
            f"combined_overlap={item.get('combined_overlap_seconds')}"
        )

    for check in owner_checks:
        print(
            f"OWNER_CHECK {check.get('status')} {check.get('name')} "
            f"overlap={check.get('combined_speech_overlap_seconds')} "
            f"min={check.get('min_required_seconds')}"
        )

    return 0 if overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
