from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.learning_corpus_hook_identifier import extract_words, normalize_text


FRONT_REACTION_KEYWORDS = {
    "boah",
    "krass",
    "alter",
    "diggah",
    "digger",
    "wallah",
    "oida",
    "junge",
    "bro",
    "alta",
    "hahaha",
    "haha",
    "lol",
    "lmao",
    "ahaha",
    "wtf",
    "omg",
    "oh mein gott",
    "wow",
    "nice",
    "geil",
    "sick",
    "fett",
    "stark",
    "fuck",
    "scheiße",
    "scheisse",
}

DE_QUESTION_STARTERS = (
    "wer ",
    "was ",
    "wie ",
    "wo ",
    "warum ",
    "wann ",
    "welche",
    "welcher",
    "seid ",
    "bist ",
    "habt ",
    "ist ",
)
EN_QUESTION_STARTERS = ("who ", "what ", "how ", "where ", "why ", "when ", "is ", "are ")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"fingerprint must be a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temp_path = path.with_name(f"{path.stem}.tmp{path.suffix}")
    temp_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temp_path.replace(path)


def classify_hook_pattern(first_words: str, language: str) -> str:
    clean = normalize_text(first_words)
    if not clean:
        return "silent_start"

    lowered = clean.lower()
    prefix = lowered[:90]
    if "?" in prefix:
        return "question"

    if language == "de":
        if any(prefix.startswith(starter) for starter in DE_QUESTION_STARTERS):
            return "question"
    if language == "en":
        if any(prefix.startswith(starter) for starter in EN_QUESTION_STARTERS):
            return "question"

    if "!" in prefix:
        return "exclamation"

    words = clean.split()[:6]
    caps_count = sum(1 for word in words if word.isupper() and len(word) > 1)
    if caps_count >= 2:
        return "exclamation"

    if any(keyword in prefix for keyword in FRONT_REACTION_KEYWORDS):
        return "high_reaction"

    return "narrative"


def first_words_from_transcript(transcript: dict[str, Any], *, max_words: int = 18) -> str:
    words = extract_words(str(transcript.get("first_10s_text", "") or ""))
    return " ".join(words[:max_words])


def rerun_hooks(
    *,
    corpus_root: Path,
    backup_dir: Path,
    limit: int | None,
) -> dict[str, Any]:
    fingerprints = sorted(corpus_root.rglob("style_fingerprint.json"))
    if limit is not None:
        fingerprints = fingerprints[:limit]

    backup_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for fingerprint_path in fingerprints:
        data = _read_json(fingerprint_path)
        label = str(fingerprint_path.parent.relative_to(corpus_root))
        backup_path = backup_dir / f"{label.replace('/', '_').replace(chr(92), '_')}_hook_pre_p4_7_5.json"
        shutil.copy2(fingerprint_path, backup_path)

        transcript = data.get("transcript", {})
        language = str(transcript.get("language", "unknown") or "unknown").lower()
        first_words = first_words_from_transcript(transcript)
        pattern_class = classify_hook_pattern(first_words, language)
        old_hook = dict(data.get("hook", {}))
        data["hook"] = {
            "first_words": first_words,
            "pattern_class": pattern_class,
        }
        data["p4_7_5_hook_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
        _write_json(fingerprint_path, data)
        results.append(
            {
                "source": label,
                "old_pattern_class": old_hook.get("pattern_class", "unknown"),
                "new_pattern_class": pattern_class,
                "first_words": first_words,
            }
        )

    return audit(corpus_root=corpus_root, results=results)


def audit(*, corpus_root: Path, results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    patterns: Counter[str] = Counter()
    ok_count = 0
    for fingerprint_path in sorted(corpus_root.rglob("style_fingerprint.json")):
        data = _read_json(fingerprint_path)
        rel = str(fingerprint_path.parent.relative_to(corpus_root))
        hook = data.get("hook", {})
        first_words = str(hook.get("first_words", "") or "")
        pattern_class = str(hook.get("pattern_class", "unknown") or "unknown")
        ok = len(first_words) >= 10 and pattern_class != "unknown"
        if ok:
            ok_count += 1
        patterns[pattern_class] += 1
        entries.append(
            {
                "source": rel,
                "ok": ok,
                "first_words_length": len(first_words),
                "pattern_class": pattern_class,
            }
        )
    return {
        "entry_count": len(entries),
        "hook_ok_count": ok_count,
        "problem_count": len(entries) - ok_count,
        "pattern_distribution": dict(sorted(patterns.items())),
        "distinct_pattern_count": len(patterns),
        "problems": [entry for entry in entries if not entry["ok"]],
        "entries": entries,
        "run_results": list(results or []),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-root", default="learning_corpus")
    parser.add_argument("--backup-dir", default="reports/phase4_7/p4_7_5_backup")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--report", default="reports/phase4_7/p4_7_5_hook_audit.json")
    args = parser.parse_args()

    report = rerun_hooks(
        corpus_root=Path(args.corpus_root),
        backup_dir=Path(args.backup_dir),
        limit=args.limit,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["hook_ok_count"] == report["entry_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
