from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(".")
REPORT_DIR = ROOT / "reports" / "phase4_8"
JSON_REPORT = REPORT_DIR / "P4_8_A5_TOP_SOLO_VLOGS_AUDIT.json"
MD_REPORT = REPORT_DIR / "P4_8_A5_TOP_SOLO_VLOGS_AUDIT.md"

EXPECTED_COUNTS = {
    "top_solo": 30,
    "vlogs": 3,
}

STYLE_CAPTURE_REQUIRED_FIELDS = {
    "cut_density_curve",
    "reaction_density",
    "opening_pattern",
    "closing_pattern",
    "audio_dynamic_range",
    "scene_duration_stats",
    "intensity_clustering",
    "signature_score",
    "cut_rhythm",
    "focus_decision_distribution",
}

CRITICAL_REQUIRED_FIELDS = {
    "audio",
    "transcript",
    "scene_changes",
    "pacing",
    "hook",
    "style_capture",
}

P4_6_RECOMMENDED_FIELDS = {
    "voice_intensity_distribution",
    "facial_expression_distribution",
    "gameplay_ratio",
    "speaker_distribution",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def collect_fingerprints(bucket: str) -> list[Path]:
    root = ROOT / "learning_corpus" / bucket
    if not root.exists():
        return []
    return sorted(root.rglob("style_fingerprint.json"))


def flatten_source_strings(value: Any, prefix: str = "") -> list[dict[str, str]]:
    found: list[dict[str, str]] = []

    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(child, str) and (
                "source" in key.lower()
                or "path" in key.lower()
                or "audio_extract" in key.lower()
            ):
                found.append({"field": child_prefix, "value": child})
            found.extend(flatten_source_strings(child, child_prefix))

    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_prefix = f"{prefix}[{index}]"
            found.extend(flatten_source_strings(child, child_prefix))

    return found


def audit_one(bucket: str, path: Path) -> dict[str, Any]:
    rel = str(path.relative_to(ROOT))
    failed: list[str] = []
    warnings: list[str] = []

    try:
        data = read_json(path)
    except Exception as exc:
        return {
            "bucket": bucket,
            "path": rel,
            "ok": False,
            "failed": ["invalid_json"],
            "warnings": [],
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }

    top_keys = set(data.keys())

    missing_critical = sorted(CRITICAL_REQUIRED_FIELDS - top_keys)
    if missing_critical:
        failed.extend([f"missing_critical_{key}" for key in missing_critical])

    missing_p4_6 = sorted(P4_6_RECOMMENDED_FIELDS - top_keys)
    if missing_p4_6:
        warnings.extend([f"missing_p4_6_recommended_{key}" for key in missing_p4_6])

    style_capture = data.get("style_capture", {})
    if not isinstance(style_capture, dict):
        failed.append("style_capture_not_object")
        missing_style = sorted(STYLE_CAPTURE_REQUIRED_FIELDS)
    else:
        missing_style = sorted(STYLE_CAPTURE_REQUIRED_FIELDS - set(style_capture.keys()))
        if missing_style:
            failed.extend([f"missing_style_capture_{key}" for key in missing_style])

    transcript = data.get("transcript", {})
    if isinstance(transcript, dict):
        if "first_10s_text" in transcript:
            warnings.append("legacy_transcript_first_10s_text_present")
        transcript_text = str(
            transcript.get("first_window_text", "")
            or transcript.get("first_10s_text", "")
            or transcript.get("text_preview", "")
            or ""
        ).strip()
        if not transcript_text:
            failed.append("transcript_text_missing")
    else:
        failed.append("transcript_not_object")

    source_strings = flatten_source_strings(data)
    bad_source_hits = []
    raw_warning_hits = []

    for item in source_strings:
        value = item["value"].replace("\\", "/").lower()

        if "raw_mixed_audio" in value:
            bad_source_hits.append({**item, "reason": "raw_mixed_audio_reference"})

        if "/pairs/" in value:
            bad_source_hits.append({**item, "reason": "pairs_bucket_reference"})

        if value.endswith("/raw.mp4"):
            raw_warning_hits.append({**item, "reason": "raw_mp4_reference"})

    if bad_source_hits:
        failed.append("bad_source_reference_found")

    if raw_warning_hits:
        warnings.append("raw_mp4_source_reference_found_review_needed")

    audio = data.get("audio", {})
    if isinstance(audio, dict):
        rms = audio.get("rms_curve_sampled", [])
        if isinstance(rms, list) and len(rms) < 10:
            warnings.append("audio_rms_curve_sparse")
    else:
        failed.append("audio_not_object")

    scene_changes = data.get("scene_changes", {})
    if isinstance(scene_changes, dict):
        if int(scene_changes.get("count", 0) or 0) <= 0:
            warnings.append("scene_change_count_zero_or_missing")
    else:
        failed.append("scene_changes_not_object")

    hook = data.get("hook", {})
    if isinstance(hook, dict):
        hook_text = str(
            hook.get("first_words", "")
            or hook.get("text_preview", "")
            or ""
        ).strip()
        if not hook_text:
            warnings.append("hook_text_missing_or_empty")
    else:
        failed.append("hook_not_object")

    speaker = data.get("speaker_distribution", {})
    speaker_source = data.get("speaker_distribution_source")
    speaker_status = speaker.get("status") if isinstance(speaker, dict) else None

    return {
        "bucket": bucket,
        "path": rel,
        "ok": not failed,
        "failed": failed,
        "warnings": warnings,
        "bad_source_hits": bad_source_hits,
        "raw_warning_hits": raw_warning_hits,
        "top_key_count": len(top_keys),
        "missing_critical": missing_critical,
        "missing_p4_6_recommended": missing_p4_6,
        "missing_style_capture": missing_style,
        "transcript_source": transcript.get("source") if isinstance(transcript, dict) else None,
        "transcript_scope": transcript.get("scope") if isinstance(transcript, dict) else None,
        "hook_source": hook.get("source") if isinstance(hook, dict) else None,
        "audio_source": audio.get("source") if isinstance(audio, dict) else None,
        "style_capture_source": style_capture.get("source") if isinstance(style_capture, dict) else None,
        "speaker_distribution_source": speaker_source,
        "speaker_distribution_status": speaker_status,
    }


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    before_hashes: dict[str, str] = {}
    bucket_results: dict[str, Any] = {}
    all_bad: list[dict[str, Any]] = []
    all_warnings: list[dict[str, Any]] = []

    for bucket, expected_count in EXPECTED_COUNTS.items():
        fps = collect_fingerprints(bucket)

        for fp in fps:
            before_hashes[str(fp.relative_to(ROOT))] = sha256_file(fp)

        entries = [audit_one(bucket, fp) for fp in fps]
        bad = [x for x in entries if not x.get("ok")]
        warnings = [x for x in entries if x.get("warnings")]

        count_ok = len(fps) == expected_count
        if not count_ok:
            bad.append({
                "bucket": bucket,
                "path": str((ROOT / "learning_corpus" / bucket).relative_to(ROOT)),
                "ok": False,
                "failed": [f"count_mismatch_expected_{expected_count}_got_{len(fps)}"],
                "warnings": [],
            })

        bucket_results[bucket] = {
            "expected_count": expected_count,
            "actual_count": len(fps),
            "count_ok": count_ok,
            "ok_count": len([x for x in entries if x.get("ok")]),
            "bad_count": len(bad),
            "warning_count": len(warnings),
            "entries": entries,
            "bad": bad,
            "warnings": warnings,
        }

        all_bad.extend(bad)
        all_warnings.extend(warnings)

    after_hashes: dict[str, str] = {}
    for bucket in EXPECTED_COUNTS:
        for fp in collect_fingerprints(bucket):
            after_hashes[str(fp.relative_to(ROOT))] = sha256_file(fp)

    mutated = [
        path for path, before in before_hashes.items()
        if after_hashes.get(path) != before
    ]

    status = "ok" if not all_bad and not mutated else "failed"

    report = {
        "phase": "P4.8-A5",
        "name": "top_solo_vlogs_audit_only",
        "status": status,
        "timestamp_utc": now_utc(),
        "mutation_check": {
            "ok": not mutated,
            "mutated_files": mutated,
        },
        "summary": {
            "top_solo_count": bucket_results.get("top_solo", {}).get("actual_count"),
            "vlogs_count": bucket_results.get("vlogs", {}).get("actual_count"),
            "hard_bad_count": len(all_bad),
            "warning_entry_count": len(all_warnings),
        },
        "buckets": bucket_results,
    }

    write_json(JSON_REPORT, report)

    md = [
        "# PROJECT ZENITH — Phase 4.8 A5 Top Solo / Vlogs Audit",
        "",
        f"Status: {status}",
        "",
        "## Summary",
        "",
        f"- top_solo count: {report['summary']['top_solo_count']} / 30",
        f"- vlogs count: {report['summary']['vlogs_count']} / 3",
        f"- hard_bad_count: {report['summary']['hard_bad_count']}",
        f"- warning_entry_count: {report['summary']['warning_entry_count']}",
        f"- mutation_check_ok: {report['mutation_check']['ok']}",
        "",
        "## Decision",
        "",
    ]

    if status == "ok":
        md.append("A5_AUDIT_PASS")
        md.append("")
        md.append("top_solo and vlogs do not need blind re-fingerprinting.")
    else:
        md.append("A5_AUDIT_REVIEW_REQUIRED")
        md.append("")
        md.append("Do not start B1/B2 until the bad entries are reviewed.")

    md.append("")
    md.append("## Bad Entries")
    md.append("")
    if all_bad:
        for item in all_bad:
            md.append(f"- {item.get('bucket')} | {item.get('path')} | {item.get('failed')}")
    else:
        md.append("- none")

    md.append("")
    md.append("## Warning Entries")
    md.append("")
    if all_warnings:
        for item in all_warnings:
            md.append(f"- {item.get('bucket')} | {item.get('path')} | {item.get('warnings')}")
    else:
        md.append("- none")

    MD_REPORT.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")

    print("=== P4.8 A5 TOP_SOLO/VLOGS AUDIT ===")
    print("status:", status)
    print("top_solo_count:", report["summary"]["top_solo_count"])
    print("vlogs_count:", report["summary"]["vlogs_count"])
    print("hard_bad_count:", report["summary"]["hard_bad_count"])
    print("warning_entry_count:", report["summary"]["warning_entry_count"])
    print("mutation_check_ok:", report["mutation_check"]["ok"])

    if all_bad:
        print("\nBAD SAMPLE:")
        for item in all_bad[:10]:
            print(item.get("bucket"), item.get("path"), item.get("failed"))

    if all_warnings:
        print("\nWARNING SAMPLE:")
        for item in all_warnings[:10]:
            print(item.get("bucket"), item.get("path"), item.get("warnings"))

    if status == "ok":
        print("\nA5_AUDIT_PASS")
    else:
        print("\nA5_AUDIT_REVIEW_REQUIRED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
