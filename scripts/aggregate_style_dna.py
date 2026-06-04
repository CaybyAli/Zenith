from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from statistics import mean, median
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.pair_track_truth_loader import get_ali_source


SCHEMA_VERSION = "p5_g3_style_dna_v1"
PAIR_TRUTH_PATH = Path("video_configs/pair_track_truth.json")
DEFAULT_CORPUS_ROOT = Path("learning_corpus")
DEFAULT_OUTPUT_DIR = Path("video_configs")

PAIR_SOLO_IDS = {
    "pair_003",
    "pair_008",
    "pair_013",
    "pair_017",
    "pair_018",
}

INTENSITY_CLUSTERING_LABELS = (
    "front_loaded",
    "burst",
    "even",
    "scattered",
    "back_loaded",
)

VOICE_OUTPUT_KEYS = ("normal", "leise_erhoeht", "schreien", "bruellen")

VOICE_ALIASES = {
    "normal": "normal",
    "leise_erhoeht": "leise_erhoeht",
    "leise_erhöht": "leise_erhoeht",
    "leicht_erhöht": "leise_erhoeht",
    "leicht_erhoeht": "leise_erhoeht",
    "schreien": "schreien",
    "schrei": "schreien",
    "brüllen": "bruellen",
    "bruellen": "bruellen",
    "bruell": "bruellen",
    "brüll": "bruellen",
}

OUTPUT_SPECS = {
    "gaming_pairs": {
        "input_dir": Path("pairs"),
        "filename": "gaming_pairs_style_dna.json",
        "expected_count": 20,
    },
    "top_solo": {
        "input_dir": Path("top_solo"),
        "filename": "top_solo_style_dna.json",
        "expected_count": None,
    },
    "vlog": {
        "input_dir": Path("vlogs"),
        "filename": "vlog_style_dna.json",
        "expected_count": None,
    },
}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.tmp{path.suffix}")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    tmp.replace(path)



def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, str):
        try:
            number = float(value.strip().replace(",", "."))
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _pct(value: Any) -> float | None:
    number = _to_float(value)
    if number is None:
        return None
    if abs(number) <= 1.5:
        number *= 100.0
    return number


def _get_path(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _numeric_from_path(payload: dict[str, Any], dotted_path: str) -> float | None:
    raw = _get_path(payload, dotted_path)
    if isinstance(raw, dict):
        for key in ("range_db", "median", "mean", "value"):
            number = _to_float(raw.get(key))
            if number is not None:
                return number
        return None
    return _to_float(raw)


def _percentile(values: list[float], fraction: float) -> float | None:
    clean = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not clean:
        return None
    if len(clean) == 1:
        return round(clean[0], 3)

    position = (len(clean) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)

    if low == high:
        return round(clean[low], 3)

    weight = position - low
    value = clean[low] * (1.0 - weight) + clean[high] * weight
    return round(value, 3)


def _summary(values: list[float]) -> dict[str, float | None]:
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return {"median": None, "p10": None, "p90": None}
    return {
        "median": round(median(clean), 3),
        "p10": _percentile(clean, 0.10),
        "p90": _percentile(clean, 0.90),
    }


def _count_distribution(values: list[str], fixed_keys: tuple[str, ...] | None = None) -> dict[str, int]:
    counter = Counter(value for value in values if value)
    if fixed_keys:
        keys = list(fixed_keys) + sorted(key for key in counter if key not in fixed_keys)
    else:
        keys = sorted(counter)
    return {key: int(counter.get(key, 0)) for key in keys}


def _label_from_pattern(raw: Any, *, kind: str) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if not isinstance(raw, dict):
        return None

    for key in ("label", "pattern", "type", "category", "dominant", "value"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    if kind == "opening":
        if raw.get("starts_with_silence") is True:
            return "silence"
        if raw.get("starts_with_question") is True:
            return "question"
        if raw.get("starts_with_action") is True:
            return "action"
        hook = raw.get("hook_pattern_class")
        if isinstance(hook, str) and hook.strip():
            return hook.strip()

    if kind == "closing":
        if raw.get("ends_with_action") is True:
            return "action"
        if raw.get("ends_with_quiet") is True:
            return "quiet"
        if raw.get("ends_with_cut") is True:
            return "cut"

    return None


def _dominant_focus_label(raw: Any) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if not isinstance(raw, dict):
        return None

    for key in ("label", "dominant", "type", "category", "value"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    candidates: dict[str, float] = {}
    for key, value in raw.items():
        if not str(key).endswith("_pct"):
            continue
        number = _to_float(value)
        if number is None:
            continue
        candidates[str(key)[:-4]] = number

    if not candidates:
        return None

    return max(candidates.items(), key=lambda item: item[1])[0]


def _transcript_first_window(payload: dict[str, Any]) -> str | None:
    transcript = payload.get("transcript")
    if not isinstance(transcript, dict):
        transcript = {}

    for key in ("first_window_text", "first_10s_text"):
        value = transcript.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for key in ("first_window_text", "first_10s_text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return None


def _voice_distribution(payload: dict[str, Any]) -> dict[str, float] | None:
    raw = payload.get("voice_intensity_distribution")
    if not isinstance(raw, dict):
        return None

    result = {key: 0.0 for key in VOICE_OUTPUT_KEYS}
    found_any = False

    for raw_key, raw_value in raw.items():
        normalized = str(raw_key).strip().lower()
        mapped = VOICE_ALIASES.get(normalized)
        if mapped is None:
            continue

        number = _to_float(raw_value)
        if number is None:
            continue

        result[mapped] = number
        found_any = True

    return result if found_any else None


def _aggregate_voice(distributions: list[dict[str, float]]) -> dict[str, float]:
    result: dict[str, float] = {}

    for key in VOICE_OUTPUT_KEYS:
        values = [dist[key] for dist in distributions if key in dist]
        result[key] = round(mean(values), 3) if values else 0.0

    return result


def _clip_histogram_bins(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: OrderedDict[str, int] = OrderedDict()

    for payload in payloads:
        raw = _get_path(payload, "pacing.clip_length_histogram_bins")

        if isinstance(raw, dict):
            iterable = [{"label": str(label), "count": count} for label, count in raw.items()]
        elif isinstance(raw, list):
            iterable = raw
        else:
            continue

        for item in iterable:
            if not isinstance(item, dict):
                continue

            label = item.get("label") or item.get("bin") or item.get("range") or item.get("name")
            if label is None and "min" in item and "max" in item:
                label = f"{item['min']}-{item['max']}s"

            count = item.get("count") if "count" in item else item.get("value", item.get("n", 0))
            label_text = str(label or "").strip()
            count_number = _to_float(count)

            if not label_text or count_number is None:
                continue

            counts.setdefault(label_text, 0)
            counts[label_text] += int(round(count_number))

    return [{"label": label, "count": count} for label, count in counts.items()]


def _pair_id_from_path(path: Path) -> str:
    return path.parent.name


def _collect_fingerprints(corpus_root: Path, relative_dir: Path) -> list[Path]:
    root = corpus_root / relative_dir
    if not root.exists():
        return []
    return sorted(root.glob("*/style_fingerprint.json"))


def _speaker_values_for_pairs(
    pair_files: list[Path],
    payloads_by_path: dict[Path, dict[str, Any]],
    pair_truth_path: Path,
) -> tuple[list[float], list[float], dict[str, str]]:
    ali_values: list[float] = []
    friend_values: list[float] = []
    ali_sources: dict[str, str] = {}

    for path in pair_files:
        pair_id = _pair_id_from_path(path)

        # Pflichtregel: Ali-Quelle kommt nur aus pair_track_truth_loader.get_ali_source().
        # speaker_distribution["track_mapping"] wird absichtlich nie gelesen.
        ali_source = get_ali_source(pair_id, pair_truth_path)
        ali_sources[pair_id] = ali_source

        if pair_id in PAIR_SOLO_IDS:
            continue

        speaker = payloads_by_path[path].get("speaker_distribution")
        if not isinstance(speaker, dict):
            continue

        ali_pct = _pct(speaker.get("ali"))
        friend_pct = _pct(speaker.get("friend"))

        if ali_pct is not None:
            ali_values.append(ali_pct)
        if friend_pct is not None:
            friend_values.append(friend_pct)

    return ali_values, friend_values, ali_sources


def _aggregate_group(
    *,
    content_type: str,
    files: list[Path],
    payloads_by_path: dict[Path, dict[str, Any]],
    pair_truth_path: Path,
) -> dict[str, Any]:
    payloads = [payloads_by_path[path] for path in files]

    cuts = [
        value
        for payload in payloads
        if (value := _numeric_from_path(payload, "pacing.cuts_per_minute")) is not None
    ]
    median_clip_seconds = [
        value
        for payload in payloads
        if (value := _numeric_from_path(payload, "pacing.median_clip_seconds")) is not None
    ]
    audio_dynamic_range = [
        value
        for payload in payloads
        if (value := _numeric_from_path(payload, "style_capture.audio_dynamic_range")) is not None
    ]

    voice_distributions = [
        dist for payload in payloads if (dist := _voice_distribution(payload)) is not None
    ]

    intensity_values = [
        str(value).strip()
        for payload in payloads
        if isinstance((value := _get_path(payload, "style_capture.intensity_clustering")), str)
        and value.strip()
    ]

    opening_values = [
        label
        for payload in payloads
        if (label := _label_from_pattern(_get_path(payload, "style_capture.opening_pattern"), kind="opening"))
    ]

    closing_values = [
        label
        for payload in payloads
        if (label := _label_from_pattern(_get_path(payload, "style_capture.closing_pattern"), kind="closing"))
    ]

    focus_values = [
        label
        for payload in payloads
        if (label := _dominant_focus_label(_get_path(payload, "style_capture.focus_decision_distribution")))
    ]

    transcript_samples = []
    for path, payload in zip(files, payloads, strict=True):
        text = _transcript_first_window(payload)
        if text is None:
            continue
        transcript_samples.append(
            {
                "source": str(path.parent.as_posix()),
                "first_window_text": text,
            }
        )

    dna: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "content_type": content_type,
        "source_count": len(files),
        "cuts_per_minute": _summary(cuts),
        "median_clip_seconds": _summary(median_clip_seconds),
        "audio_dynamic_range": _summary(audio_dynamic_range),
        "voice_intensity_distribution": _aggregate_voice(voice_distributions),
        "intensity_clustering": _count_distribution(
            intensity_values,
            fixed_keys=INTENSITY_CLUSTERING_LABELS,
        ),
        "opening_pattern": _count_distribution(opening_values),
        "closing_pattern": _count_distribution(closing_values),
        "clip_length_histogram": _clip_histogram_bins(payloads),
        "focus_decision_distribution": _count_distribution(focus_values),
        "first_window_text": transcript_samples,
    }

    if content_type == "gaming_pairs":
        ali_values, friend_values, ali_sources = _speaker_values_for_pairs(
            files,
            payloads_by_path,
            pair_truth_path,
        )

        dna["ali_source_truth"] = str(pair_truth_path.as_posix())
        dna["speaker_distribution"] = {
            "ali_median_pct": _summary(ali_values)["median"],
            "friend_median_pct": _summary(friend_values)["median"],
        }
        dna["speaker_distribution_duo_source_count"] = len(ali_values)
        dna["speaker_distribution_excluded_solos"] = sorted(PAIR_SOLO_IDS)
        dna["ali_source_by_pair"] = dict(sorted(ali_sources.items()))

    return dna


def build_style_dna(
    *,
    corpus_root: str | Path = DEFAULT_CORPUS_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    pair_truth_path: str | Path = PAIR_TRUTH_PATH,
) -> dict[str, Any]:
    corpus_root = Path(corpus_root)
    output_dir = Path(output_dir)
    pair_truth_path = Path(pair_truth_path)

    result: dict[str, Any] = {}

    for content_type, spec in OUTPUT_SPECS.items():
        files = _collect_fingerprints(corpus_root, spec["input_dir"])
        payloads_by_path = {path: _read_json(path) for path in files}

        dna = _aggregate_group(
            content_type=content_type,
            files=files,
            payloads_by_path=payloads_by_path,
            pair_truth_path=pair_truth_path,
        )

        output_path = output_dir / str(spec["filename"])
        _write_json(output_path, dna)

        result[content_type] = {
            "output_path": output_path,
            "dna": dna,
        }

    return result


def _format_float(value: Any) -> str:
    number = _to_float(value)
    return "n/a" if number is None else f"{number:.2f}"


def _print_plausibility(result: dict[str, Any]) -> None:
    pairs = result["gaming_pairs"]["dna"]
    top_solo = result["top_solo"]["dna"]
    vlog = result["vlog"]["dna"]

    print(f"Pairs eingelesen: {pairs['source_count']}/20")
    print(f"top_solo eingelesen: {top_solo['source_count']}/?")
    print(f"vlogs eingelesen: {vlog['source_count']}/?")
    print(
        "gaming_pairs cuts_per_minute Median: "
        f"{_format_float(pairs['cuts_per_minute']['median'])} "
        "(Erwartung laut Referenz: ~6-10)"
    )
    print(
        "gaming_pairs ali% Median: "
        f"{_format_float(pairs['speaker_distribution']['ali_median_pct'])} "
        "(Erwartung: ~60-70%)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate existing learning_corpus style_fingerprint.json files into Style-DNA JSONs."
    )
    parser.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--pair-truth-path", default=str(PAIR_TRUTH_PATH))
    args = parser.parse_args(argv)

    result = build_style_dna(
        corpus_root=args.corpus_root,
        output_dir=args.output_dir,
        pair_truth_path=args.pair_truth_path,
    )
    _print_plausibility(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())