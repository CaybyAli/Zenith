from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.gaming_pipeline import resolve_track_roles
from core.llm_brain import LLMBrain
from core.profile_manager import ProfileManager
from core.reaction_focus_decisions import refine_friend_reaction_candidates
from core.reaction_shadow_report import (
    build_a2_reaction_candidates,
    build_shadow_report,
)
from core.transcript_processor import TranscriptProcessor


DEFAULT_PAIR_ID = "pair_009"
DEFAULT_RAW_VIDEO_PATH = ROOT / "learning_corpus" / "pairs" / DEFAULT_PAIR_ID / "raw.mp4"
DEFAULT_JOB_PATH = ROOT / "exports" / "gaming_main" / "job_f3ed8b2f34d9" / "job.json"
OUTPUT_DIR = ROOT / "reports" / "blockd_a2b3a_shadow"
DEFAULT_OUTPUT_PATH = OUTPUT_DIR / f"{DEFAULT_PAIR_ID}_shadow_report.json"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _default_raw_path(pair_id: str) -> Path:
    return ROOT / "learning_corpus" / "pairs" / pair_id / "raw.mp4"


def _default_output_path(pair_id: str) -> Path:
    return OUTPUT_DIR / f"{pair_id}_shadow_report.json"


def _default_job_path(pair_id: str) -> Path | None:
    if pair_id == DEFAULT_PAIR_ID:
        return DEFAULT_JOB_PATH
    return None


def _resolve_path(path: Path | None, default_path: Path | None) -> Path | None:
    resolved = path if path is not None else default_path
    if resolved is None:
        return None
    if not resolved.is_absolute():
        return ROOT / resolved
    return resolved


def _find_discord_plus_game_role(
    roles: list[Any] | None,
    *,
    pair_id: str,
    required: bool = True,
) -> Any | None:
    for role in roles or []:
        if getattr(role, "role", None) == "discord_plus_game":
            return role
    if required:
        raise RuntimeError(f"No discord_plus_game track role found for {pair_id}")
    return None


def _resolve_audio_stream_index(
    processor: TranscriptProcessor,
    raw_video_path: Path,
    role: Any,
) -> tuple[int, dict[str, Any]]:
    inventory = processor.audio_stream_inspector.inspect(str(raw_video_path))
    audio_ordinal = int(getattr(role, "ffmpeg_audio_index"))
    if audio_ordinal < 0 or audio_ordinal >= len(inventory.streams):
        raise RuntimeError(
            f"A2 audio ordinal {audio_ordinal} out of range for "
            f"{len(inventory.streams)} audio streams"
        )
    return int(inventory.streams[audio_ordinal].index), inventory.to_dict()


def _resolve_absolute_audio_stream_index(
    processor: TranscriptProcessor,
    raw_video_path: Path,
    stream_index: int,
) -> tuple[int, dict[str, Any]]:
    inventory = processor.audio_stream_inspector.inspect(str(raw_video_path))
    available = [int(stream.index) for stream in inventory.streams]
    if int(stream_index) not in available:
        raise RuntimeError(
            f"Friend audio stream index {stream_index} not found; "
            f"available streams: {available}"
        )
    return int(stream_index), inventory.to_dict()


def _normalize_transcript_segments(segments: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for source_index, segment in enumerate(segments):
        payload = _payload(segment)
        start = _number(payload, "start", "start_seconds")
        end = _number(payload, "end", "end_seconds")
        normalized.append(
            {
                "source_index": source_index,
                "start": round(start, 3),
                "end": round(end, 3),
                "text": str(payload.get("text") or "").strip(),
                "speaker": str(payload.get("speaker") or "unknown"),
                "audio_track": str(payload.get("audio_track") or "discord"),
                "words": _normalize_words(payload.get("words") or []),
            }
        )
    return normalized


def _payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if callable(getattr(value, "to_dict", None)):
        payload = value.to_dict()
        if isinstance(payload, dict):
            return payload
    return asdict(value)


def _normalize_words(raw_words: list[Any]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for raw_word in raw_words:
        payload = _payload(raw_word)
        try:
            start = _number(payload, "start", "start_seconds")
            end = _number(payload, "end", "end_seconds")
        except (TypeError, ValueError):
            continue
        text = str(payload.get("word", payload.get("text", "")) or "").strip()
        if not text or end <= start:
            continue
        words.append(
            {
                "word": text,
                "start": round(start, 3),
                "end": round(end, 3),
                "probability": payload.get("probability"),
            }
        )
    return words


def _number(payload: dict[str, Any], *names: str) -> float:
    for name in names:
        value = payload.get(name)
        if value is not None:
            return float(value)
    raise ValueError(f"Missing numeric field {names}: {payload!r}")


def _job_context(
    *,
    pair_id: str,
    job_payload: dict[str, Any],
    raw_video_path: Path,
    a2_role: Any | None,
    a2_audio_stream_index: int,
    accepted_count: int,
) -> dict[str, Any]:
    return {
        "pair_id": pair_id,
        "job_id": job_payload.get("job_id"),
        "channel_type": job_payload.get("channel_type", "gaming_main"),
        "raw_video_path": str(raw_video_path),
        "a2_role": getattr(a2_role, "role", None),
        "a2_ffmpeg_audio_index": (
            int(getattr(a2_role, "ffmpeg_audio_index"))
            if getattr(a2_role, "ffmpeg_audio_index", None) is not None
            else None
        ),
        "a2_audio_stream_index": int(a2_audio_stream_index),
        "accepted_candidate_count": int(accepted_count),
        "shadow_report_chain": "a2_segments_to_presence_refine_to_llm_decide_reactions",
        "picker_policy": {
            "version": "Ali 2026-06-22",
            "mode": "nearly_every_strong_friend_moment_but_strict",
            "positive_triggers": [
                "hype",
                "shock",
                "victory_shout",
                "funny",
                "lost",
                "dry",
            ],
            "reject": "generic_sentences_and_non_reactions",
            "count_cap": "none",
            "density_limit": "none",
            "never_fill_to_target_count": True,
            "never_drop_genuine_moments_for_density": True,
        },
    }


def _print_summary(report_path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    print(f"report_path: {report_path}")
    print(
        "summary: "
        f"candidates={summary['candidate_count']} "
        f"accepted={summary['accepted_count']} "
        f"selected={summary['selected_count']}"
    )
    picks = [row for row in report["candidates"] if row.get("is_real_reaction") is True]
    if not picks:
        print("picks: none")
        return

    print("picks:")
    for row in picks:
        print(
            "  "
            f"{float(row['start']):.3f}-{float(row['end']):.3f} "
            f"mode={row.get('zoom_mode') or '-'} "
            f"is_real={str(row.get('is_real_reaction')).lower()} "
            f"conf={float(row.get('confidence') or 0.0):.3f} "
            f"friend_text={row.get('friend_text')}"
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-id", default=DEFAULT_PAIR_ID)
    parser.add_argument("--friend-stream-index", type=int, default=None)
    parser.add_argument("--raw", type=Path, default=None)
    parser.add_argument("--job", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv[1:])

    pair_id = str(args.pair_id).strip()
    if not pair_id:
        raise ValueError("--pair-id must not be empty")

    raw_video_path = _resolve_path(args.raw, _default_raw_path(pair_id))
    assert raw_video_path is not None
    if not raw_video_path.exists():
        raise FileNotFoundError(f"Raw video missing: {raw_video_path}")

    job_path = _resolve_path(args.job, _default_job_path(pair_id))
    job_payload = _load_json(job_path) if job_path is not None and job_path.exists() else {}

    profile = ProfileManager().load_profile("gaming_main")
    track_roles = resolve_track_roles(str(raw_video_path), profile)
    transcript_processor = TranscriptProcessor()
    if args.friend_stream_index is None:
        a2_role = _find_discord_plus_game_role(
            track_roles,
            pair_id=pair_id,
            required=True,
        )
        a2_audio_stream_index, stream_inventory = _resolve_audio_stream_index(
            transcript_processor,
            raw_video_path,
            a2_role,
        )
        stream_index_source = "track_role_discord_plus_game_ffmpeg_audio_index"
    else:
        a2_role = _find_discord_plus_game_role(
            track_roles,
            pair_id=pair_id,
            required=False,
        )
        a2_audio_stream_index, stream_inventory = _resolve_absolute_audio_stream_index(
            transcript_processor,
            raw_video_path,
            args.friend_stream_index,
        )
        stream_index_source = "cli_absolute_friend_stream_index"

    transcript = transcript_processor.transcribe(
        str(raw_video_path),
        audio_stream_index=a2_audio_stream_index,
    )
    a2_segments = _normalize_transcript_segments(transcript.segments)
    candidates = build_a2_reaction_candidates(a2_segments)

    with transcript_processor._selected_audio_source(
        str(raw_video_path),
        a2_audio_stream_index,
    ) as selected_audio:
        accepted, rejected_silence, presence_policy = refine_friend_reaction_candidates(
            candidates,
            friend_segments=a2_segments,
            a2_audio_path=Path(selected_audio.source_path),
        )

    job_context = _job_context(
        pair_id=pair_id,
        job_payload=job_payload,
        raw_video_path=raw_video_path,
        a2_role=a2_role,
        a2_audio_stream_index=a2_audio_stream_index,
        accepted_count=len(accepted),
    )
    decision = LLMBrain(timeout_seconds=60).decide_reactions(accepted, job_context)
    report = build_shadow_report(
        accepted,
        rejected_silence,
        presence_policy,
        decision.selections,
        meta={
            "pair_id": pair_id,
            "job_id": job_payload.get("job_id"),
            "job_path": str(job_path) if job_path is not None else None,
            "raw_video_path": str(raw_video_path),
            "transcript_engine": transcript.engine,
            "transcript_language": transcript.language,
            "a2_role": getattr(a2_role, "role", None),
            "a2_audio_track": getattr(a2_role, "audio_track", None),
            "a2_role_ffmpeg_audio_index": (
                int(getattr(a2_role, "ffmpeg_audio_index"))
                if getattr(a2_role, "ffmpeg_audio_index", None) is not None
                else None
            ),
            "a2_audio_stream_index": a2_audio_stream_index,
            "a2_audio_stream_index_source": stream_index_source,
            "stream_inventory": stream_inventory,
            "candidate_chain": "a2_segments_enumerate_source_index_refine_decide_shadow_report",
            "model_used": decision.model_used,
            "warnings": list(decision.warnings),
        },
    )

    out_path = _resolve_path(args.out, _default_output_path(pair_id))
    assert out_path is not None
    _write_json(out_path, report)
    _print_summary(out_path, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
