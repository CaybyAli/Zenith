from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


SEMANTIC_CONTENT_LAYER_VERSION = "semantic_content_layer_v1"
SEMANTIC_CONTENT_SOURCE = "semantic_content_layer_v1_deterministic"


@dataclass(frozen=True)
class SemanticContentConfig:
    provider: str = "heuristic"
    pause_boundary_percentile: float = 0.70
    min_pause_boundary_seconds: float = 0.35
    max_pause_boundary_seconds: float = 1.20
    sentence_end_pause_seconds: float = 0.20
    thought_gap_seconds: float = 2.0
    max_utterance_seconds: float = 14.0
    max_words_per_utterance: int = 34
    silence_gap_min_seconds: float = 0.80
    dead_relevance_percentile: float = 0.25
    llm_base_url: str = "http://localhost:8080"
    llm_model: str = "local"
    llm_timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "SemanticContentConfig":
        return cls(
            provider=os.environ.get("ZENITH_SEMANTIC_PROVIDER", "heuristic"),
            llm_base_url=os.environ.get("ZENITH_SEMANTIC_LLM_BASE_URL", "http://localhost:8080"),
            llm_model=os.environ.get("ZENITH_SEMANTIC_LLM_MODEL", "local"),
        )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip())
    except Exception:
        return default
    return number if math.isfinite(number) else default


def _round(value: Any, digits: int = 3) -> float:
    return round(max(0.0, _safe_float(value)), digits)


def _start_end(item: Mapping[str, Any]) -> tuple[float, float] | None:
    start = item.get("start_seconds", item.get("start", item.get("start_time", item.get("begin"))))
    end = item.get("end_seconds", item.get("end", item.get("end_time", item.get("stop"))))

    if start is None or end is None:
        return None

    start_f = _round(start)
    end_f = _round(end)
    if end_f <= start_f:
        return None
    return start_f, end_f


def _duration(start: float, end: float) -> float:
    return _round(end - start)


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _percentile(values: list[float], q: float) -> float:
    clean = sorted(value for value in values if math.isfinite(value))
    if not clean:
        return 0.0
    if len(clean) == 1:
        return clean[0]

    pos = (len(clean) - 1) * q
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return clean[low]

    frac = pos - low
    return clean[low] * (1.0 - frac) + clean[high] * frac


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def normalize_intervals(raw: Any, *, source: str = "unknown") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                walk(item)
            return

        if isinstance(value, Mapping):
            se = _start_end(value)
            if se is not None:
                start, end = se
                row = dict(value)
                row["start_seconds"] = start
                row["end_seconds"] = end
                row["duration_seconds"] = _duration(start, end)
                row.setdefault("source", source)
                rows.append(row)
                return

            for child in value.values():
                if isinstance(child, (list, Mapping)):
                    walk(child)

    walk(raw)
    rows.sort(key=lambda row: (row["start_seconds"], row["end_seconds"], str(row.get("id", ""))))
    return rows


def normalize_words(raw: Any) -> list[dict[str, Any]]:
    candidates: list[Any]
    if isinstance(raw, list):
        candidates = raw
    elif isinstance(raw, Mapping):
        if isinstance(raw.get("words"), list):
            candidates = raw["words"]
        elif isinstance(raw.get("word_timestamps"), list):
            candidates = raw["word_timestamps"]
        elif isinstance(raw.get("segments"), list):
            candidates = []
            for segment in raw["segments"]:
                if isinstance(segment, Mapping) and isinstance(segment.get("words"), list):
                    candidates.extend(segment["words"])
        else:
            candidates = []
    else:
        candidates = []

    words: list[dict[str, Any]] = []
    for index, item in enumerate(candidates):
        if not isinstance(item, Mapping):
            continue
        se = _start_end(item)
        text = str(item.get("word", item.get("text", ""))).strip()
        if se is None or not text:
            continue
        start, end = se
        words.append(
            {
                "word_index": int(item.get("word_index", index)),
                "word": text,
                "start_seconds": start,
                "end_seconds": end,
                "confidence": item.get("confidence"),
            }
        )

    words.sort(key=lambda row: (row["start_seconds"], row["end_seconds"], row["word_index"]))
    return words


def merge_intervals(rows: list[Mapping[str, Any]], gap_tolerance: float = 0.05) -> list[dict[str, Any]]:
    normalized = normalize_intervals(rows)
    if not normalized:
        return []

    merged: list[dict[str, Any]] = []
    cur_start = normalized[0]["start_seconds"]
    cur_end = normalized[0]["end_seconds"]

    for row in normalized[1:]:
        start = row["start_seconds"]
        end = row["end_seconds"]
        if start <= cur_end + gap_tolerance:
            cur_end = max(cur_end, end)
        else:
            merged.append({"start_seconds": _round(cur_start), "end_seconds": _round(cur_end)})
            cur_start = start
            cur_end = end

    merged.append({"start_seconds": _round(cur_start), "end_seconds": _round(cur_end)})
    return merged


def _clean_token(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = cleaned.replace("Ã¤", "ä").replace("Ã¶", "ö").replace("Ã¼", "ü").replace("ÃŸ", "ß")
    cleaned = re.sub(r"^[^\wäöüß]+|[^\wäöüß]+$", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _word_text(words: list[Mapping[str, Any]]) -> str:
    return " ".join(str(word.get("word") or "").strip() for word in words).strip()


def _tokens(text: str) -> list[str]:
    return [token for token in (_clean_token(part) for part in text.split()) if token]


def _contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    normalized = " ".join(_tokens(text))
    return any(phrase in normalized for phrase in phrases)


FILLER_TOKENS = {
    "äh",
    "ähm",
    "eh",
    "ehm",
    "um",
    "uh",
    "ja",
    "jo",
    "okay",
    "ok",
    "ne",
    "nee",
    "naja",
    "also",
    "halt",
    "so",
    "genau",
    "warte",
    "sorry",
}

EVENT_TOKENS = {
    "links",
    "rechts",
    "oben",
    "unten",
    "hinten",
    "vorne",
    "gegner",
    "enemy",
    "spieler",
    "einer",
    "jemand",
    "kommt",
    "kommen",
    "schießt",
    "schiesst",
    "schuss",
    "hit",
    "tot",
    "down",
    "boden",
    "abgeschossen",
    "rückendeckung",
    "deckung",
    "heil",
    "heilen",
}

EMOTION_TOKENS = {
    "gott",
    "nein",
    "digga",
    "lol",
    "krass",
    "geisteskrank",
    "wild",
    "krank",
    "alter",
    "scheiße",
    "scheisse",
}

CALLOUT_PHRASES = (
    "da ist",
    "da sind",
    "bei dir",
    "hinter dir",
    "links ein",
    "rechts ein",
    "zu boden",
    "ich bin tot",
    "ich brauche",
    "komm her",
    "hier lang",
)


def _raw_semantic_features(text: str) -> dict[str, Any]:
    tokens = _tokens(text)
    token_count = len(tokens)
    unique_content = sorted({token for token in tokens if token not in FILLER_TOKENS})
    filler_count = sum(1 for token in tokens if token in FILLER_TOKENS)
    event_count = sum(1 for token in tokens if token in EVENT_TOKENS)
    emotion_count = sum(1 for token in tokens if token in EMOTION_TOKENS)
    has_callout_phrase = _contains_phrase(text, CALLOUT_PHRASES)
    has_question = "?" in text
    has_exclaim = "!" in text
    has_repeat = token_count >= 2 and len(set(tokens)) <= max(1, token_count // 2)

    filler_share = filler_count / max(1, token_count)
    content_density = len(unique_content) / max(1, token_count)

    is_event_callout = bool(event_count > 0 or has_callout_phrase)
    is_emotional = bool(emotion_count > 0 or has_exclaim)

    raw = 0.16
    raw += min(0.22, 0.035 * len(unique_content))
    raw += 0.26 if is_event_callout else 0.0
    raw += 0.18 if is_emotional else 0.0
    raw += 0.08 if has_question and content_density >= 0.35 else 0.0
    raw -= 0.22 if filler_share >= 0.60 else 0.0
    raw -= 0.10 if has_repeat and not is_event_callout and not is_emotional else 0.0
    raw -= 0.08 if token_count <= 2 and not is_event_callout and not is_emotional else 0.0

    likely_filler = bool(
        token_count <= 4
        and filler_share >= 0.50
        and not is_event_callout
        and not is_emotional
        and not has_question
    )

    return {
        "tokens": tokens,
        "token_count": token_count,
        "unique_content_count": len(unique_content),
        "filler_count": filler_count,
        "filler_share": round(filler_share, 6),
        "event_token_count": event_count,
        "emotion_token_count": emotion_count,
        "has_callout_phrase": has_callout_phrase,
        "has_question": has_question,
        "has_exclaim": has_exclaim,
        "likely_filler": likely_filler,
        "is_event_callout": is_event_callout,
        "is_emotional": is_emotional,
        "raw_relevance": round(_clamp(raw), 6),
    }


def _adaptive_pause_boundary(words: list[dict[str, Any]], config: SemanticContentConfig) -> float:
    gaps: list[float] = []
    for left, right in zip(words, words[1:]):
        gap = _safe_float(right["start_seconds"]) - _safe_float(left["end_seconds"])
        if gap > 0:
            gaps.append(gap)

    if not gaps:
        return config.max_pause_boundary_seconds

    boundary = _percentile(gaps, config.pause_boundary_percentile)
    boundary = _clamp(
        boundary,
        config.min_pause_boundary_seconds,
        config.max_pause_boundary_seconds,
    )
    return round(boundary, 3)


def _same_speaker_language(left: dict[str, Any], right: dict[str, Any]) -> bool:
    def pick(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = row.get(key)
            if value is not None and str(value).strip():
                return str(value).strip().lower()
        return None

    left_speaker = pick(left, ("speaker", "speaker_id", "track", "source"))
    right_speaker = pick(right, ("speaker", "speaker_id", "track", "source"))
    left_language = pick(left, ("language", "lang"))
    right_language = pick(right, ("language", "lang"))

    has_speaker = left_speaker is not None and right_speaker is not None
    has_language = left_language is not None and right_language is not None
    if not has_speaker and not has_language:
        return False
    if has_speaker and left_speaker != right_speaker:
        return False
    if has_language and left_language != right_language:
        return False
    return True


def build_utterances(
    words_raw: Any,
    speech_regions_raw: Any | None = None,
    *,
    config: SemanticContentConfig | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = config or SemanticContentConfig.from_env()
    raw_word_rows_for_metadata = words_raw if isinstance(words_raw, list) else []
    words = normalize_words(words_raw)
    if raw_word_rows_for_metadata:
        for index, word_row in enumerate(words):
            if index >= len(raw_word_rows_for_metadata):
                break
            raw_row = raw_word_rows_for_metadata[index]
            if not isinstance(raw_row, Mapping):
                continue
            for key in ("speaker", "speaker_id", "track", "source", "language", "lang"):
                value = raw_row.get(key)
                if value is not None and str(value).strip() and key not in word_row:
                    word_row[key] = value

    speech_regions = merge_intervals(normalize_intervals(speech_regions_raw or [], source="speech_region"))
    pause_boundary = _adaptive_pause_boundary(words, config)

    utterances: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    def flush(reason: str) -> None:
        if not current:
            return
        start = _round(current[0]["start_seconds"])
        end = _round(current[-1]["end_seconds"])
        utterances.append(
            {
                "utterance_id": f"utt_{len(utterances) + 1:05d}",
                "start_seconds": start,
                "end_seconds": end,
                "duration_seconds": _duration(start, end),
                "text": _word_text(current),
                "word_count": len(current),
                "word_start_index": current[0]["word_index"],
                "word_end_index": current[-1]["word_index"],
                "thought_boundary": {
                    "start": True,
                    "end": True,
                    "reason": reason,
                },
                "source": SEMANTIC_CONTENT_SOURCE,
            }
        )
        current.clear()

    for word in words:
        if not current:
            current.append(word)
            continue

        previous = current[-1]
        gap = _safe_float(word["start_seconds"]) - _safe_float(previous["end_seconds"])
        current_duration = _safe_float(word["end_seconds"]) - _safe_float(current[0]["start_seconds"])
        previous_text = str(previous.get("word") or "").strip()
        sentence_end = previous_text.endswith((".", "!", "?", "..."))

        same_speaker_language = _same_speaker_language(previous, word)
        short_same_thought_gap = bool(
            gap >= 0.0
            and gap < config.thought_gap_seconds
            and same_speaker_language
        )
        pause_or_sentence_boundary = bool(
            gap >= pause_boundary
            or (sentence_end and gap >= config.sentence_end_pause_seconds)
        )
        should_split = bool(
            (pause_or_sentence_boundary and not short_same_thought_gap)
            or current_duration >= config.max_utterance_seconds
            or len(current) >= config.max_words_per_utterance
        )
        if should_split:
            reason = "pause_or_sentence_boundary"
            if current_duration >= config.max_utterance_seconds:
                reason = "max_utterance_duration"
            elif len(current) >= config.max_words_per_utterance:
                reason = "max_words_per_utterance"
            flush(reason)

        current.append(word)

    flush("final_utterance")

    metadata = {
        "word_count": len(words),
        "speech_region_count": len(speech_regions),
        "pause_boundary_seconds": pause_boundary,
        "utterance_count": len(utterances),
    }
    return utterances, metadata


def build_silence_units(
    speech_regions_raw: Any,
    *,
    video_duration_seconds: float | None = None,
    config: SemanticContentConfig | None = None,
) -> list[dict[str, Any]]:
    config = config or SemanticContentConfig.from_env()
    speech = merge_intervals(normalize_intervals(speech_regions_raw or [], source="speech_region"))
    if not speech:
        return []

    end_limit = _safe_float(video_duration_seconds, speech[-1]["end_seconds"])
    gaps: list[tuple[float, float]] = []
    cursor = 0.0

    for row in speech:
        start = row["start_seconds"]
        end = row["end_seconds"]
        if start - cursor >= config.silence_gap_min_seconds:
            gaps.append((_round(cursor), _round(start)))
        cursor = max(cursor, end)

    if end_limit - cursor >= config.silence_gap_min_seconds:
        gaps.append((_round(cursor), _round(end_limit)))

    return [
        {
            "utterance_id": f"silence_{index:05d}",
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": _duration(start, end),
            "text": "",
            "word_count": 0,
            "relevance_score": 0.0,
            "is_dead_or_filler": True,
            "is_event_callout": False,
            "is_emotional": False,
            "thought_boundary": {"start": True, "end": True, "reason": "vad_silence_gap"},
            "semantic_reasons": ["vad_silence_gap"],
            "source": SEMANTIC_CONTENT_SOURCE,
        }
        for index, (start, end) in enumerate(gaps, start=1)
    ]


def _score_utterances_heuristic(
    utterances: list[dict[str, Any]],
    *,
    config: SemanticContentConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    feature_rows = [_raw_semantic_features(row.get("text", "")) for row in utterances]
    raw_values = [row["raw_relevance"] for row in feature_rows]
    p10 = _percentile(raw_values, 0.10)
    p90 = _percentile(raw_values, 0.90)
    p_dead = _percentile(raw_values, config.dead_relevance_percentile)
    denom = max(0.001, p90 - p10)

    scored: list[dict[str, Any]] = []
    for row, features in zip(utterances, feature_rows):
        raw_relevance = _safe_float(features["raw_relevance"])
        adaptive_score = _clamp((raw_relevance - p10) / denom)
        if features["is_event_callout"]:
            adaptive_score = max(adaptive_score, 0.72)
        if features["is_emotional"]:
            adaptive_score = max(adaptive_score, 0.62)

        reasons: list[str] = []
        if features["likely_filler"]:
            reasons.append("likely_filler")
        if raw_relevance <= p_dead and not features["is_event_callout"] and not features["is_emotional"]:
            reasons.append("low_adaptive_relevance")
        if features["is_event_callout"]:
            reasons.append("event_callout")
        if features["is_emotional"]:
            reasons.append("emotional_reaction")

        is_dead_or_filler = bool(
            "likely_filler" in reasons
            or (
                "low_adaptive_relevance" in reasons
                and features["token_count"] <= 5
                and not features["has_question"]
            )
        )

        enriched = dict(row)
        enriched.update(
            {
                "relevance_score": round(adaptive_score, 6),
                "raw_relevance_score": round(raw_relevance, 6),
                "is_dead_or_filler": is_dead_or_filler,
                "is_event_callout": bool(features["is_event_callout"]),
                "is_emotional": bool(features["is_emotional"]),
                "semantic_reasons": reasons or ["neutral_content"],
                "semantic_features": {
                    key: value
                    for key, value in features.items()
                    if key not in {"tokens"}
                },
            }
        )
        scored.append(enriched)

    thresholds = {
        "raw_relevance_p10": round(p10, 6),
        "raw_relevance_p90": round(p90, 6),
        "raw_dead_percentile": config.dead_relevance_percentile,
        "raw_dead_threshold": round(p_dead, 6),
        "provider": "heuristic_local_rules_v1",
    }
    return scored, thresholds


def _llm_prompt_payload(utterances: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task": "Score spoken gaming-video utterances semantically without using game-specific rules.",
        "required_json_schema": {
            "utterances": [
                {
                    "utterance_id": "string",
                    "relevance_score": "float 0..1",
                    "is_dead_or_filler": "bool",
                    "is_event_callout": "bool",
                    "thought_boundary_start": "bool",
                    "thought_boundary_end": "bool",
                }
            ]
        },
        "utterances": [
            {
                "utterance_id": row["utterance_id"],
                "start_seconds": row["start_seconds"],
                "end_seconds": row["end_seconds"],
                "text": row.get("text", ""),
            }
            for row in utterances
        ],
    }


def _score_utterances_openai_compatible(
    utterances: list[dict[str, Any]],
    *,
    config: SemanticContentConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    body = {
        "model": config.llm_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You score transcript utterances for a gaming highlight edit. "
                    "Be game-agnostic. Return only JSON. Do not include chain-of-thought."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(_llm_prompt_payload(utterances), ensure_ascii=False),
            },
        ],
        "temperature": 0,
        "top_p": 1,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        config.llm_base_url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.llm_timeout_seconds) as response:
        raw_response = json.loads(response.read().decode("utf-8"))

    content = raw_response["choices"][0]["message"]["content"]
    parsed = json.loads(content) if isinstance(content, str) else content
    llm_rows = parsed.get("utterances") if isinstance(parsed, Mapping) else None
    if not isinstance(llm_rows, list):
        raise ValueError("LLM semantic response missing utterances list")

    by_id = {
        str(row.get("utterance_id")): row
        for row in llm_rows
        if isinstance(row, Mapping)
    }
    scored: list[dict[str, Any]] = []
    for row in utterances:
        llm = by_id.get(str(row["utterance_id"]), {})
        enriched = dict(row)
        relevance = _clamp(_safe_float(llm.get("relevance_score"), 0.0))
        thought = dict(enriched.get("thought_boundary") or {})
        thought["start"] = bool(llm.get("thought_boundary_start", thought.get("start", True)))
        thought["end"] = bool(llm.get("thought_boundary_end", thought.get("end", True)))
        thought["reason"] = "llm_structured_json"
        enriched.update(
            {
                "relevance_score": round(relevance, 6),
                "raw_relevance_score": round(relevance, 6),
                "is_dead_or_filler": bool(llm.get("is_dead_or_filler", False)),
                "is_event_callout": bool(llm.get("is_event_callout", False)),
                "is_emotional": False,
                "thought_boundary": thought,
                "semantic_reasons": ["llm_structured_json"],
            }
        )
        scored.append(enriched)

    thresholds = {
        "provider": "openai_compatible_llm",
        "llm_base_url": config.llm_base_url,
        "llm_model": config.llm_model,
        "temperature": 0,
        "dependency": "local_or_api_openai_compatible_chat_completions",
    }
    return scored, thresholds


SemanticScorer = Callable[[list[dict[str, Any]], SemanticContentConfig], tuple[list[dict[str, Any]], dict[str, Any]]]


def score_utterances(
    utterances: list[dict[str, Any]],
    *,
    config: SemanticContentConfig | None = None,
    scorer: SemanticScorer | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = config or SemanticContentConfig.from_env()

    if scorer is not None:
        return scorer(utterances, config)

    provider = str(config.provider or "heuristic").strip().lower()
    if provider in {"openai", "openai_compatible", "llm"}:
        return _score_utterances_openai_compatible(utterances, config=config)
    if provider != "heuristic":
        raise ValueError(f"unsupported semantic provider: {config.provider}")
    return _score_utterances_heuristic(utterances, config=config)


def input_fingerprint(
    *,
    words_raw: Any,
    speech_regions_raw: Any,
    video_duration_seconds: float | None,
    config: SemanticContentConfig,
) -> str:
    payload = {
        "version": SEMANTIC_CONTENT_LAYER_VERSION,
        "config": asdict(config),
        "words": normalize_words(words_raw),
        "speech_regions": normalize_intervals(speech_regions_raw or [], source="speech_region"),
        "video_duration_seconds": video_duration_seconds,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def analyze_semantic_content(
    *,
    words_raw: Any,
    speech_regions_raw: Any,
    video_duration_seconds: float | None = None,
    config: SemanticContentConfig | None = None,
    cache_path: str | Path | None = None,
    scorer: SemanticScorer | None = None,
) -> dict[str, Any]:
    config = config or SemanticContentConfig.from_env()
    fingerprint = input_fingerprint(
        words_raw=words_raw,
        speech_regions_raw=speech_regions_raw,
        video_duration_seconds=video_duration_seconds,
        config=config,
    )

    cache = Path(cache_path) if cache_path is not None else None
    if cache is not None and cache.exists():
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("input_fingerprint") == fingerprint:
            return cached

    utterances, segmentation = build_utterances(
        words_raw,
        speech_regions_raw,
        config=config,
    )
    scored_utterances, scoring_metadata = score_utterances(
        utterances,
        config=config,
        scorer=scorer,
    )
    silence_units = build_silence_units(
        speech_regions_raw,
        video_duration_seconds=video_duration_seconds,
        config=config,
    )

    all_units = sorted(
        [*scored_utterances, *silence_units],
        key=lambda row: (row["start_seconds"], row["end_seconds"], row["utterance_id"]),
    )
    dead_units = [row for row in all_units if bool(row.get("is_dead_or_filler"))]
    thought_boundaries = [
        {
            "utterance_id": row["utterance_id"],
            "start_seconds": row["start_seconds"],
            "end_seconds": row["end_seconds"],
            "text": row.get("text", ""),
            "thought_boundary": row.get("thought_boundary") or {},
        }
        for row in scored_utterances
    ]

    output = {
        "version": SEMANTIC_CONTENT_LAYER_VERSION,
        "source": SEMANTIC_CONTENT_SOURCE,
        "input_fingerprint": fingerprint,
        "config": asdict(config),
        "provider": scoring_metadata.get("provider", config.provider),
        "dependency_note": (
            "heuristic provider has no external API cost"
            if scoring_metadata.get("provider") == "heuristic_local_rules_v1"
            else "LLM provider is external/local API dependent and cached"
        ),
        "segmentation": segmentation,
        "scoring": scoring_metadata,
        "utterances": scored_utterances,
        "silence_units": silence_units,
        "semantic_units": all_units,
        "dead_or_filler_units": dead_units,
        "thought_boundaries": thought_boundaries,
        "summary": {
            "utterance_count": len(scored_utterances),
            "silence_unit_count": len(silence_units),
            "dead_or_filler_count": len(dead_units),
            "event_callout_count": len([row for row in scored_utterances if row.get("is_event_callout")]),
            "provider": scoring_metadata.get("provider", config.provider),
        },
    }

    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    return output
