from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any

INTENSITY_CLUSTERING_TAXONOMY = (
    "front_loaded",
    "burst",
    "even",
    "scattered",
    "back_loaded",
)

VOICE_INTENSITY_TAXONOMY = (
    "normal",
    "leise_erhoeht",
    "schreien",
    "bruellen",
)

EXPECTED_SOURCE_COUNTS = {
    "gaming_pairs": 20,
    "top_solo": 30,
    "vlog": 3,
}

OUTPUT_FILENAMES = {
    "gaming_pairs": "gaming_pairs_style_dna.json",
    "top_solo": "top_solo_style_dna.json",
    "vlog": "vlog_style_dna.json",
}

EXCLUDED_CORPUS_DIR_NAMES = (
    "pairs_singletrack_backup",
)

REFERENCE_40 = {
    "cuts_per_minute_median": 6.6,
    "cuts_per_minute_mean": 9.1,
    "scene_length_seconds_median": 4.1,
    "audio_dynamic_range_db_mean": 27.0,
    "voice_distribution_percent": {
        "normal": 69.0,
        "leise_erhoeht": 24.0,
        "schreien": 6.0,
        "bruellen": 1.0,
    },
    "hook_counts": {
        "narrative": 31,
        "high_reaction": 5,
        "question": 4,
    },
    "intensity_clustering_counts": {
        "front_loaded": 15,
        "burst": 14,
        "even": 5,
        "scattered": 3,
        "back_loaded": 3,
    },
}

CUTS_PER_MINUTE_KEYS = (
    "cuts_per_minute",
    "cuts_per_min",
    "cut_rate_per_minute",
    "cut_rate_per_min",
    "cuts_minute",
)

SCENE_LENGTH_KEYS = (
    "median_scene_length_seconds",
    "scene_length_median_seconds",
    "median_scene_duration_seconds",
    "median_scene_length",
    "median_scene_duration",
)

AUDIO_DYNAMIC_RANGE_KEYS = (
    "audio_dynamic_range_db",
    "audio_dynamics_db",
    "dynamic_range_db",
    "audio_dynamic_db",
)

VOICE_INTENSITY_KEYS = (
    "voice_intensity",
    "opening_voice_intensity",
    "dominant_voice_intensity",
)

HOOK_KEYS = (
    "hook_type",
    "opening_hook_type",
    "hook_category",
    "hook",
)

INTENSITY_CLUSTERING_KEYS = (
    "intensity_clustering",
    "intensity_cluster",
    "intensity_distribution_type",
)

FOCUS_KEYS = (
    "focus",
    "dominant_focus",
    "visual_focus",
    "focus_mode",
)

OPENING_KEYS = (
    "opening",
    "opening_type",
    "opening_style",
    "opening_category",
)

TRANSCRIPT_ALIAS_KEYS = (
    "first_window_text",
    "first_10s_text",
)


def _norm_key(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _norm_category(value: object) -> str:
    text = str(value or "").strip().lower()
    text = (
        text.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def _walk_key_values(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key), child
            yield from _walk_key_values(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_key_values(child)


def _walk_path_values(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield child_path, child
            yield from _walk_path_values(child, child_path)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_path_values(child, f"{path}[]")


def _first_path_value(payload: dict[str, Any], paths: tuple[str, ...]) -> Any:
    for dotted_path in paths:
        current: Any = payload
        ok = True
        for part in dotted_path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                ok = False
                break
        if ok:
            return current
    return None


def _first_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    wanted = {_norm_key(key) for key in keys}
    for key, value in _walk_key_values(payload):
        if _norm_key(key) in wanted:
            return value
    return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, str):
        cleaned = value.strip().replace(",", ".")
        try:
            number = float(cleaned)
            return number if math.isfinite(number) else None
        except ValueError:
            return None
    if isinstance(value, dict):
        for key in ("median", "mean", "avg", "average", "value"):
            number = _to_float(value.get(key))
            if number is not None:
                return number
    return None


def _extract_number(payload: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    exact = _to_float(_first_value(payload, keys))
    if exact is not None:
        return exact

    wanted_parts = [_norm_key(key) for key in keys]
    for key, value in _walk_key_values(payload):
        norm = _norm_key(key)
        if any(part in norm for part in wanted_parts):
            number = _to_float(value)
            if number is not None:
                return number

    return None


def _extract_category(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    value = _first_value(payload, keys)
    if isinstance(value, str) and value.strip():
        return _norm_category(value)
    if isinstance(value, dict):
        for key in ("type", "category", "label", "value", "dominant"):
            child = value.get(key)
            if isinstance(child, str) and child.strip():
                return _norm_category(child)
    return None


def _resolve_transcript_alias(payload: dict[str, Any]) -> dict[str, Any]:
    for key in TRANSCRIPT_ALIAS_KEYS:
        value = _first_value(payload, (key,))
        text = str(value or "").strip()
        if text:
            return {
                "resolved_key": key,
                "is_non_empty": True,
                "preview": text[:180],
                "char_count": len(text),
                "word_count": len(text.split()),
            }

    return {
        "resolved_key": None,
        "is_non_empty": False,
        "preview": "",
        "char_count": 0,
        "word_count": 0,
    }


def _is_excluded_source_file(path: Path, corpus_root: Path) -> bool:
    try:
        relative_parts = path.relative_to(corpus_root).parts
    except ValueError:
        relative_parts = path.parts

    return any(part in EXCLUDED_CORPUS_DIR_NAMES for part in relative_parts)


def _classify_content_type(path: Path) -> str:
    text = path.as_posix().lower()
    if "top_solo" in text or "top-solo" in text or "topsolo" in text:
        return "top_solo"
    if "vlog" in text:
        return "vlog"
    if "pair" in text:
        return "gaming_pairs"
    return "unknown"


def _speaker_distribution(payload: dict[str, Any]) -> dict[str, Any]:
    raw = _first_value(payload, ("speaker_distribution", "speaker_mix", "speaker_share"))
    if not isinstance(raw, dict):
        raw = {}

    ali = _to_float(raw.get("ali"))
    friend = _to_float(raw.get("friend"))

    if ali is None:
        ali = _extract_number(payload, ("ali_speech_share", "ali_ratio", "ali_percent"))
    if friend is None:
        friend = _extract_number(payload, ("friend_speech_share", "friend_ratio", "friend_percent"))

    values = {}
    if ali is not None:
        values["ali"] = ali
    if friend is not None:
        values["friend"] = friend

    total = sum(values.values())
    shares = {}
    if total > 0:
        if total > 1.5:
            shares = {key: round(value / total, 4) for key, value in values.items()}
        else:
            shares = {key: round(value, 4) for key, value in values.items()}

    return {
        "raw": values,
        "shares": shares,
    }


def _extract_scene_length_seconds(payload: dict[str, Any]) -> float | None:
    value = _to_float(_first_path_value(payload, (
        "style_capture.scene_duration_stats.median_seconds",
        "scene_duration_stats.median_seconds",
    )))
    if value is not None:
        return value
    return _extract_number(payload, SCENE_LENGTH_KEYS)


def _extract_audio_dynamic_range_db(payload: dict[str, Any]) -> float | None:
    value = _to_float(_first_path_value(payload, (
        "style_capture.audio_dynamic_range.range_db",
        "audio_dynamic_range.range_db",
    )))
    if value is not None:
        return value
    return _extract_number(payload, AUDIO_DYNAMIC_RANGE_KEYS)


def _extract_voice_distribution(payload: dict[str, Any]) -> dict[str, float]:
    raw = _first_path_value(payload, ("voice_intensity_distribution",))
    values: dict[str, float] = {}

    if isinstance(raw, dict):
        for key in VOICE_INTENSITY_TAXONOMY:
            number = _to_float(raw.get(key))
            if number is not None:
                values[key] = round(number, 3)

    if values:
        return values

    flat = _extract_category(payload, VOICE_INTENSITY_KEYS)
    if flat in VOICE_INTENSITY_TAXONOMY:
        return {
            key: 100.0 if key == flat else 0.0
            for key in VOICE_INTENSITY_TAXONOMY
        }

    opening_voice = _first_path_value(
        payload,
        ("style_capture.opening_pattern.voice_intensity_first_5s",),
    )
    opening_voice_norm = _norm_category(opening_voice)
    if opening_voice_norm in VOICE_INTENSITY_TAXONOMY:
        return {
            key: 100.0 if key == opening_voice_norm else 0.0
            for key in VOICE_INTENSITY_TAXONOMY
        }

    return {}


def _dominant_percent_category(values: dict[str, float]) -> str | None:
    if not values:
        return None
    return max(values.items(), key=lambda item: item[1])[0]


def _extract_hook_category(payload: dict[str, Any]) -> str | None:
    value = _first_path_value(payload, (
        "hook.pattern_class",
        "style_capture.opening_pattern.hook_pattern_class",
    ))
    if isinstance(value, str) and value.strip():
        return _norm_category(value)
    return _extract_category(payload, HOOK_KEYS)


def _extract_focus_category(payload: dict[str, Any]) -> str | None:
    dist = _first_path_value(payload, ("style_capture.focus_decision_distribution",))
    if isinstance(dist, dict):
        candidates = {
            "balanced": _to_float(dist.get("balanced_pct")) or 0.0,
            "drop": _to_float(dist.get("drop_pct")) or 0.0,
            "facecam": _to_float(dist.get("facecam_pct")) or 0.0,
            "gameplay": _to_float(dist.get("gameplay_pct")) or 0.0,
        }
        if any(value > 0 for value in candidates.values()):
            return max(candidates.items(), key=lambda item: item[1])[0]

    return _extract_category(payload, FOCUS_KEYS)


def _extract_opening_category(payload: dict[str, Any]) -> str | None:
    opening = _first_path_value(payload, ("style_capture.opening_pattern",))
    if isinstance(opening, dict):
        if opening.get("starts_with_question") is True:
            return "question"
        if opening.get("starts_with_action") is True:
            return "action"
        if opening.get("starts_with_silence") is True:
            return "silence"

        hook = opening.get("hook_pattern_class")
        if isinstance(hook, str) and hook.strip():
            return _norm_category(hook)

    return _extract_category(payload, OPENING_KEYS)


def _aggregate_voice_distribution(distributions: list[dict[str, float]]) -> dict[str, Any]:
    if not distributions:
        return {
            "total": 0,
            "counts": {},
            "percent": {},
            "median_percent": {},
            "source_count_by_category": {},
        }

    percent: dict[str, float] = {}
    median_percent: dict[str, float] = {}
    source_count_by_category: dict[str, int] = {}

    for key in VOICE_INTENSITY_TAXONOMY:
        values = [
            float(dist[key])
            for dist in distributions
            if key in dist and dist[key] is not None
        ]
        source_count_by_category[key] = len(values)
        if values:
            percent[key] = round(mean(values), 3)
            median_percent[key] = round(median(values), 3)
        else:
            percent[key] = 0.0
            median_percent[key] = 0.0

    dominant_counts = Counter(
        _dominant_percent_category(dist)
        for dist in distributions
        if _dominant_percent_category(dist)
    )

    return {
        "total": len(distributions),
        "counts": {key: int(dominant_counts.get(key, 0)) for key in VOICE_INTENSITY_TAXONOMY},
        "percent": percent,
        "median_percent": median_percent,
        "source_count_by_category": source_count_by_category,
    }


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return round(ordered[0], 3)

    pos = (len(ordered) - 1) * p
    low = math.floor(pos)
    high = math.ceil(pos)
    if low == high:
        return round(ordered[low], 3)

    weight = pos - low
    value = ordered[low] * (1.0 - weight) + ordered[high] * weight
    return round(value, 3)


def _numeric_summary(values: list[float]) -> dict[str, Any]:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not clean:
        return {
            "count": 0,
            "median": None,
            "p10": None,
            "p90": None,
            "mean": None,
            "min": None,
            "max": None,
        }

    return {
        "count": len(clean),
        "median": round(median(clean), 3),
        "p10": _percentile(clean, 0.10),
        "p90": _percentile(clean, 0.90),
        "mean": round(mean(clean), 3),
        "min": round(min(clean), 3),
        "max": round(max(clean), 3),
    }


def _histogram(values: list[str], allowed_values: tuple[str, ...] | None = None) -> dict[str, Any]:
    counter = Counter(value for value in values if value)
    if allowed_values:
        ordered_keys = list(allowed_values) + sorted(
            key for key in counter.keys() if key not in allowed_values
        )
    else:
        ordered_keys = sorted(counter.keys())

    total = sum(counter.values())
    counts = {key: int(counter.get(key, 0)) for key in ordered_keys}
    percent = {
        key: round((counts[key] / total) * 100.0, 2) if total else 0.0
        for key in ordered_keys
    }

    return {
        "total": total,
        "counts": counts,
        "percent": percent,
    }


def _nested_correlation(left_values: list[str | None], right_values: list[str | None]) -> dict[str, Any]:
    table: dict[str, Counter] = defaultdict(Counter)
    total = 0

    for left, right in zip(left_values, right_values):
        if not left or not right:
            continue
        table[left][right] += 1
        total += 1

    return {
        "pair_count": total,
        "counts": {
            left: dict(counter.most_common())
            for left, counter in sorted(table.items())
        },
    }


def _reference_check(kind: str, summary: dict[str, Any]) -> dict[str, Any]:
    signals: list[dict[str, Any]] = []

    cuts_median = summary["numeric"]["cuts_per_minute"]["median"]
    if cuts_median is not None:
        ref = REFERENCE_40["cuts_per_minute_median"]
        diff_pct = abs(cuts_median - ref) / ref * 100.0
        if diff_pct > 15.0:
            signals.append({
                "field": "cuts_per_minute.median",
                "value": cuts_median,
                "reference": ref,
                "deviation_percent": round(diff_pct, 2),
                "explanation": "quality_signal_not_auto_error: subset/style split can differ from 40er reference",
            })

    scene_median = summary["numeric"]["scene_length_seconds"]["median"]
    if scene_median is not None:
        ref = REFERENCE_40["scene_length_seconds_median"]
        diff_pct = abs(scene_median - ref) / ref * 100.0
        if diff_pct > 15.0:
            signals.append({
                "field": "scene_length_seconds.median",
                "value": scene_median,
                "reference": ref,
                "deviation_percent": round(diff_pct, 2),
                "explanation": "quality_signal_not_auto_error: content type may have different pacing",
            })

    audio_mean = summary["numeric"]["audio_dynamic_range_db"]["mean"]
    if audio_mean is not None:
        ref = REFERENCE_40["audio_dynamic_range_db_mean"]
        diff_pct = abs(audio_mean - ref) / ref * 100.0
        if diff_pct > 15.0:
            signals.append({
                "field": "audio_dynamic_range_db.mean",
                "value": audio_mean,
                "reference": ref,
                "deviation_percent": round(diff_pct, 2),
                "explanation": "quality_signal_not_auto_error: content type may have different audio dynamics",
            })

    voice_percent = summary["distributions"]["voice_intensity"]["percent"]
    for key, ref in REFERENCE_40["voice_distribution_percent"].items():
        value = float(voice_percent.get(key, 0.0))
        diff_pp = abs(value - ref)
        if diff_pp > 5.0:
            signals.append({
                "field": f"voice_intensity.{key}",
                "value_percent": value,
                "reference_percent": ref,
                "deviation_pp": round(diff_pp, 2),
                "explanation": "quality_signal_not_auto_error: source mix differs or voice taxonomy shifted",
            })

    return {
        "reference_name": "40er_reference",
        "reference": REFERENCE_40,
        "signals_requiring_explanation": signals,
        "signal_count": len(signals),
        "note": "Deviations are explanatory quality signals, not automatic failures.",
        "vlog_note": "Vlog sample is descriptive only; n=3 is too small for clustering." if kind == "vlog" else None,
    }



def _extract_source(path: Path, corpus_root: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    kind = _classify_content_type(path)
    transcript = _resolve_transcript_alias(payload)

    intensity = _first_path_value(payload, ("style_capture.intensity_clustering",))
    if not isinstance(intensity, str) or not intensity.strip():
        intensity = _extract_category(payload, INTENSITY_CLUSTERING_KEYS)
    else:
        intensity = _norm_category(intensity)

    if intensity and intensity not in INTENSITY_CLUSTERING_TAXONOMY:
        intensity = f"unknown_existing_value:{intensity}"

    voice_distribution = _extract_voice_distribution(payload)

    return {
        "path": str(path.relative_to(corpus_root)),
        "content_type": kind,
        "cuts_per_minute": _extract_number(payload, CUTS_PER_MINUTE_KEYS),
        "scene_length_seconds": _extract_scene_length_seconds(payload),
        "audio_dynamic_range_db": _extract_audio_dynamic_range_db(payload),
        "voice_intensity": _dominant_percent_category(voice_distribution),
        "voice_intensity_distribution": voice_distribution,
        "hook": _extract_hook_category(payload),
        "intensity_clustering": intensity,
        "focus": _extract_focus_category(payload),
        "opening": _extract_opening_category(payload),
        "transcript_alias": transcript,
        "speaker_distribution": _speaker_distribution(payload),
    }


def _aggregate_kind(kind: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    cuts = [source["cuts_per_minute"] for source in sources if source["cuts_per_minute"] is not None]
    scenes = [source["scene_length_seconds"] for source in sources if source["scene_length_seconds"] is not None]
    audio = [source["audio_dynamic_range_db"] for source in sources if source["audio_dynamic_range_db"] is not None]

    voice_distributions = [
        source["voice_intensity_distribution"]
        for source in sources
        if source["voice_intensity_distribution"]
    ]
    hook_values = [source["hook"] for source in sources if source["hook"]]
    intensity_values = [
        source["intensity_clustering"]
        for source in sources
        if source["intensity_clustering"]
    ]

    transcript_key_counts = Counter(
        source["transcript_alias"]["resolved_key"] or "missing"
        for source in sources
    )
    transcript_non_empty_count = sum(
        1 for source in sources if source["transcript_alias"]["is_non_empty"]
    )

    speaker_shares = defaultdict(list)
    for source in sources:
        shares = source["speaker_distribution"]["shares"]
        for speaker, value in shares.items():
            speaker_shares[speaker].append(float(value))

    summary = {
        "schema_version": "p5_g3_style_dna_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "content_type": kind,
        "source_count": len(sources),
        "expected_source_count": EXPECTED_SOURCE_COUNTS.get(kind),
        "is_descriptive_only": kind == "vlog",
        "read_only_input": True,
        "notes": [
            "Aggregated from existing style_fingerprint.json files.",
            "No new clustering is invented.",
            "intensity_clustering is counted as existing taxonomy frequency only.",
            "Transcript aliases first_window_text and first_10s_text are normalized.",
            "Voice intensity is aggregated from voice_intensity_distribution percentages.",
        ],
        "numeric": {
            "cuts_per_minute": _numeric_summary(cuts),
            "scene_length_seconds": _numeric_summary(scenes),
            "audio_dynamic_range_db": _numeric_summary(audio),
        },
        "distributions": {
            "voice_intensity": _aggregate_voice_distribution(voice_distributions),
            "hook": _histogram(hook_values),
            "intensity_clustering": _histogram(
                intensity_values,
                allowed_values=INTENSITY_CLUSTERING_TAXONOMY,
            ),
        },
        "correlations": {
            "voice_intensity_to_focus": _nested_correlation(
                [source["voice_intensity"] for source in sources],
                [source["focus"] for source in sources],
            ),
            "hook_to_opening": _nested_correlation(
                [source["hook"] for source in sources],
                [source["opening"] for source in sources],
            ),
        },
        "transcript_key_resolution": {
            "alias_keys": list(TRANSCRIPT_ALIAS_KEYS),
            "key_counts": dict(sorted(transcript_key_counts.items())),
            "non_empty_count": transcript_non_empty_count,
            "all_sources_non_empty": transcript_non_empty_count == len(sources),
            "sample_previews": [
                {
                    "source": source["path"],
                    **source["transcript_alias"],
                }
                for source in sources[:5]
            ],
        },
        "source_files": [source["path"] for source in sources],
    }

    if kind == "gaming_pairs":
        summary["speaker_distribution"] = {
            speaker: _numeric_summary(values)
            for speaker, values in sorted(speaker_shares.items())
        }

    summary["reference_check"] = _reference_check(kind, summary)
    return summary

def build_style_dna(
    corpus_root: str | Path = "learning_corpus",
    output_dir: str | Path = "video_configs",
    strict_counts: bool = True,
) -> dict[str, Any]:
    corpus_root = Path(corpus_root)
    output_dir = Path(output_dir)

    discovered_files = sorted(corpus_root.rglob("style_fingerprint.json"))
    excluded_files = [
        path for path in discovered_files
        if _is_excluded_source_file(path, corpus_root)
    ]
    files = [
        path for path in discovered_files
        if not _is_excluded_source_file(path, corpus_root)
    ]
    sources = [_extract_source(path, corpus_root) for path in files]

    unknown = [source for source in sources if source["content_type"] == "unknown"]
    if unknown:
        raise RuntimeError(
            "Unknown style_fingerprint content type: "
            + ", ".join(source["path"] for source in unknown)
        )

    grouped = {
        kind: [source for source in sources if source["content_type"] == kind]
        for kind in EXPECTED_SOURCE_COUNTS
    }

    if strict_counts:
        total_expected = sum(EXPECTED_SOURCE_COUNTS.values())
        if len(sources) != total_expected:
            raise RuntimeError(f"Expected {total_expected} fingerprints, got {len(sources)}")
        for kind, expected in EXPECTED_SOURCE_COUNTS.items():
            actual = len(grouped[kind])
            if actual != expected:
                raise RuntimeError(f"Expected {expected} {kind} fingerprints, got {actual}")

    output_dir.mkdir(parents=True, exist_ok=True)

    dna_by_kind = {}
    output_files = {}
    for kind, group_sources in grouped.items():
        dna = _aggregate_kind(kind, group_sources)
        dna_by_kind[kind] = dna
        output_path = output_dir / OUTPUT_FILENAMES[kind]
        output_path.write_text(
            json.dumps(dna, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        output_files[kind] = str(output_path)

    manifest = {
        "schema_version": "p5_g3_style_dna_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "corpus_root": str(corpus_root),
        "output_dir": str(output_dir),
        "discovered_source_count": len(discovered_files),
        "excluded_source_count": len(excluded_files),
        "excluded_source_files": [
            str(path.relative_to(corpus_root)) for path in excluded_files
        ],
        "total_source_count": len(sources),
        "expected_total_source_count": sum(EXPECTED_SOURCE_COUNTS.values()),
        "source_counts": {kind: len(grouped[kind]) for kind in EXPECTED_SOURCE_COUNTS},
        "expected_source_counts": EXPECTED_SOURCE_COUNTS,
        "output_files": output_files,
        "transcript_non_empty_counts": {
            kind: dna_by_kind[kind]["transcript_key_resolution"]["non_empty_count"]
            for kind in EXPECTED_SOURCE_COUNTS
        },
    }

    manifest_path = output_dir / "style_dna_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "manifest": manifest,
        "manifest_path": str(manifest_path),
        "dna": dna_by_kind,
    }


__all__ = [
    "INTENSITY_CLUSTERING_TAXONOMY",
    "EXPECTED_SOURCE_COUNTS",
    "build_style_dna",
]
