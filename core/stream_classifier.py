from __future__ import annotations

from typing import Any

from models.file_info import FileInfo
from models.stream_info import StreamClassificationResult, StreamInfo


VOICE_KEYWORDS = {
    "mic",
    "microphone",
    "mikro",
    "stimme",
    "voice",
    "kommentar",
    "commentary",
}

GAME_KEYWORDS = {
    "game",
    "desktop",
    "system",
    "spiel",
    "gameplay",
}

DISCORD_KEYWORDS = {
    "discord",
    "teamspeak",
    "party",
    "chat",
    "voice chat",
}

MUSIC_KEYWORDS = {
    "music",
    "musik",
    "browser",
    "alerts",
    "alert",
}


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None

    try:
        return int(value)
    except Exception:
        return None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def _parse_fps(value: Any) -> float | None:
    if not value:
        return None

    raw = str(value).strip()

    if "/" in raw:
        left, right = raw.split("/", 1)
        try:
            numerator = float(left)
            denominator = float(right)
            if denominator == 0:
                return None
            return round(numerator / denominator, 3)
        except Exception:
            return None

    try:
        return round(float(raw), 3)
    except Exception:
        return None


def _stream_text_blob(stream: dict[str, Any]) -> str:
    parts: list[str] = []

    for key in ["codec_name", "title", "handler_name"]:
        value = stream.get(key)
        if value:
            parts.append(str(value))

    tags = stream.get("tags") or {}
    if isinstance(tags, dict):
        for key, value in tags.items():
            parts.append(str(key))
            parts.append(str(value))

    return " ".join(parts).lower()


def _stream_info_text_blob(stream: StreamInfo) -> str:
    return _stream_text_blob(
        {
            "codec_name": stream.codec_name,
            "title": stream.title,
            "handler_name": stream.handler_name,
            "tags": stream.tags,
        }
    )


def _contains_any(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def extract_stream_infos_from_ffprobe(ffprobe_data: dict[str, Any]) -> list[StreamInfo]:
    if not isinstance(ffprobe_data, dict):
        ffprobe_data = {}

    streams = ffprobe_data.get("streams") or []
    if not isinstance(streams, list):
        streams = []

    result: list[StreamInfo] = []

    for stream in streams:
        if not isinstance(stream, dict):
            continue

        tags = stream.get("tags") or {}
        if not isinstance(tags, dict):
            tags = {}

        result.append(
            StreamInfo(
                index=_parse_int(stream.get("index")),
                codec_type=stream.get("codec_type"),
                codec_name=stream.get("codec_name"),
                width=_parse_int(stream.get("width")),
                height=_parse_int(stream.get("height")),
                fps=_parse_fps(
                    stream.get("r_frame_rate")
                    or stream.get("avg_frame_rate")
                ),
                channels=_parse_int(stream.get("channels")),
                sample_rate=_parse_int(stream.get("sample_rate")),
                duration_seconds=_parse_float(stream.get("duration")),
                language=stream.get("language") or tags.get("language"),
                title=stream.get("title") or tags.get("title"),
                handler_name=stream.get("handler_name") or tags.get("handler_name"),
                tags=tags,
            )
        )

    return result


def classify_stream_info(
    stream: StreamInfo,
    audio_position: int = 0,
    video_position: int = 0,
) -> StreamInfo:
    stream.reasons = []

    if stream.codec_type == "video":
        if video_position == 0 and stream.width is not None and stream.height is not None:
            stream.role = "video_primary"
            stream.confidence = 0.9
            stream.reasons.append("first_video_stream")
            return stream

        if video_position == 0:
            stream.role = "video_unknown"
            stream.confidence = 0.35
            stream.reasons.append("first_video_stream_without_resolution")
            return stream

        stream.role = "video_secondary"
        stream.confidence = 0.6
        stream.reasons.append("additional_video_stream")
        return stream

    if stream.codec_type == "audio":
        text = _stream_info_text_blob(stream)

        if _contains_any(text, VOICE_KEYWORDS):
            stream.role = "audio_candidate_voice"
            stream.confidence = 0.85
            stream.reasons.append("matched_voice_keyword")
            return stream

        if _contains_any(text, GAME_KEYWORDS):
            stream.role = "audio_candidate_game"
            stream.confidence = 0.85
            stream.reasons.append("matched_game_keyword")
            return stream

        if _contains_any(text, DISCORD_KEYWORDS):
            stream.role = "audio_candidate_discord"
            stream.confidence = 0.85
            stream.reasons.append("matched_discord_keyword")
            return stream

        if _contains_any(text, MUSIC_KEYWORDS):
            stream.role = "audio_candidate_music"
            stream.confidence = 0.85
            stream.reasons.append("matched_music_keyword")
            return stream

        if audio_position == 0:
            stream.role = "audio_primary"
            stream.confidence = 0.45
            stream.reasons.append("first_audio_stream_without_tags")
            return stream

        stream.role = "audio_unknown"
        stream.confidence = 0.2
        stream.reasons.append("audio_stream_without_known_role")
        return stream

    stream.role = "unknown"
    stream.confidence = 0.0
    stream.reasons.append("unsupported_or_missing_codec_type")
    return stream


def _add_warning_once(warnings: list[str], warning: str) -> None:
    if warning not in warnings:
        warnings.append(warning)


def classify_file_streams(file_info: FileInfo) -> StreamClassificationResult:
    stream_infos = extract_stream_infos_from_ffprobe(file_info.raw_ffprobe)

    video_position = 0
    audio_position = 0
    classified: list[StreamInfo] = []

    for stream in stream_infos:
        if stream.codec_type == "video":
            classified.append(
                classify_stream_info(stream, video_position=video_position)
            )
            video_position += 1
            continue

        if stream.codec_type == "audio":
            classified.append(
                classify_stream_info(stream, audio_position=audio_position)
            )
            audio_position += 1
            continue

        classified.append(classify_stream_info(stream))

    video_streams = [
        stream.to_dict()
        for stream in classified
        if stream.codec_type == "video"
    ]
    audio_streams = [
        stream.to_dict()
        for stream in classified
        if stream.codec_type == "audio"
    ]

    primary_video_stream = next(
        (
            stream
            for stream in video_streams
            if stream.get("role") == "video_primary"
        ),
        None,
    )
    primary_audio_stream = next(
        (
            stream
            for stream in audio_streams
            if stream.get("role") == "audio_primary"
        ),
        None,
    )

    voice_audio_candidates = [
        stream
        for stream in audio_streams
        if stream.get("role") == "audio_candidate_voice"
    ]
    game_audio_candidates = [
        stream
        for stream in audio_streams
        if stream.get("role") == "audio_candidate_game"
    ]
    discord_audio_candidates = [
        stream
        for stream in audio_streams
        if stream.get("role") == "audio_candidate_discord"
    ]
    music_audio_candidates = [
        stream
        for stream in audio_streams
        if stream.get("role") == "audio_candidate_music"
    ]
    unknown_audio_streams = [
        stream
        for stream in audio_streams
        if stream.get("role") == "audio_unknown"
    ]

    warnings: list[str] = []

    if not classified:
        _add_warning_once(warnings, "no_streams_found")

    if not video_streams:
        _add_warning_once(warnings, "no_video_stream")

    if len(audio_streams) > 1 and not voice_audio_candidates:
        _add_warning_once(warnings, "multiple_audio_streams_without_voice_candidate")

    if unknown_audio_streams:
        _add_warning_once(warnings, "unknown_audio_streams_present")

    needs_manual_review = False
    if "no_streams_found" in warnings:
        needs_manual_review = True
    if "no_video_stream" in warnings:
        needs_manual_review = True
    if "multiple_audio_streams_without_voice_candidate" in warnings:
        needs_manual_review = True
    if "unknown_audio_streams_present" in warnings:
        needs_manual_review = True
    if primary_video_stream is None:
        needs_manual_review = True

    return StreamClassificationResult(
        file_path=file_info.path,
        stream_count=len(classified),
        video_streams=video_streams,
        audio_streams=audio_streams,
        primary_video_stream=primary_video_stream,
        primary_audio_stream=primary_audio_stream,
        voice_audio_candidates=voice_audio_candidates,
        game_audio_candidates=game_audio_candidates,
        discord_audio_candidates=discord_audio_candidates,
        music_audio_candidates=music_audio_candidates,
        unknown_audio_streams=unknown_audio_streams,
        warnings=warnings,
        needs_manual_review=needs_manual_review,
    )
