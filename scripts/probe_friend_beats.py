from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.friend_reaction_beats import build
from models.transcript_result import TranscriptSegment


DEFAULT_TRANSCRIPT = (
    ROOT
    / "exports"
    / "gaming_main"
    / "job_16a0b837cbf8"
    / "transcript_segments.json"
)


def _segments_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        raw = payload.get("segments")
        return raw if isinstance(raw, list) else []
    return payload if isinstance(payload, list) else []


def _segment_from_dict(raw: dict[str, Any]) -> TranscriptSegment:
    return TranscriptSegment(
        start_seconds=float(raw.get("start_seconds", raw.get("start", 0.0)) or 0.0),
        end_seconds=float(raw.get("end_seconds", raw.get("end", 0.0)) or 0.0),
        text=str(raw.get("text") or ""),
        confidence=raw.get("confidence"),
        audio_track=str(raw.get("audio_track") or "mic"),
        speaker=str(raw.get("speaker") or "unknown"),
    )


def main(argv: list[str]) -> int:
    transcript_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_TRANSCRIPT
    payload = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
    segments = [
        _segment_from_dict(item)
        for item in _segments_payload(payload)
        if isinstance(item, dict)
    ]

    beats = build(segments)
    reaction_count = sum(
        1 for beat in beats if beat.beat_type == "friend_reaction_keyword"
    )
    call_pause_count = sum(
        1 for beat in beats if beat.beat_type == "owner_call_pause_friend"
    )

    print(f"transcript: {transcript_path}")
    print(f"segments: {len(segments)}")
    print(
        f"friend_reaction_beats: count={len(beats)} "
        f"reaction={reaction_count} call_pause={call_pause_count}"
    )
    for index, beat in enumerate(beats[:10], start=1):
        data = beat.to_dict()
        evidence = data.get("evidence", {})
        keyword = evidence.get("keyword", "-") if isinstance(evidence, dict) else "-"
        gap = evidence.get("gap_seconds", "-") if isinstance(evidence, dict) else "-"
        print(
            f"{index:02d}. {data['start']:.3f}-{data['end']:.3f} "
            f"{data['beat_type']} keyword={keyword} gap={gap} "
            f"ali={data['ali_context_text']!r} friend={data['friend_text']!r}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
