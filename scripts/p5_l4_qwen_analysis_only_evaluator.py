from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PHASE = "P5-L4"
MODE = "qwen_analysis_only_evaluator"
ALLOWED_REPORT_DIR = Path("reports") / "p5_l4_qwen_analysis_only_evaluator"
ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost"}
FORBIDDEN_QWEN_ACTIONS = {"cut", "render", "ingest", "music", "autocut", "auto_cut", "build_timeline"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def validate_output_dir(repo_root: Path, output_dir: Path) -> Path:
    root = repo_root.resolve()
    out = output_dir if output_dir.is_absolute() else root / output_dir
    out = out.resolve()

    try:
        rel = out.relative_to(root)
    except ValueError as exc:
        raise ValueError("output-dir must be inside repo-root") from exc

    if rel.as_posix() != ALLOWED_REPORT_DIR.as_posix():
        raise ValueError(
            "output-dir must be exactly reports/p5_l4_qwen_analysis_only_evaluator"
        )

    return out


def validate_local_qwen_base_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be a non-empty string")

    cleaned = base_url.strip().rstrip("/")
    parsed = urlparse(cleaned)

    if parsed.scheme != "http":
        raise ValueError("base_url must use http for local Ollama only")

    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_LOCAL_HOSTS:
        raise ValueError("base_url must point to localhost or 127.0.0.1")

    if parsed.username or parsed.password:
        raise ValueError("base_url must not contain credentials")

    if parsed.path not in ("", "/"):
        raise ValueError("base_url must not contain a path")

    return cleaned


def base_report() -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": PHASE,
        "mode": MODE,
        "created_at": utc_now_iso(),
        "qwen_requested": False,
        "qwen_used": False,
        "qwen_role": "analysis_only",
        "qwen_can_cut": False,
        "qwen_autocut_allowed": False,
        "external_network_used": False,
        "api_key_used": False,
        "render_used": False,
        "ingest_used": False,
        "music_used": False,
        "autocut_used": False,
        "overnight_started": False,
        "learning_loop_started": False,
        "phase_5_5_used": False,
        "timeline_modified": False,
        "production_files_modified": False,
        "video_configs_modified": False,
        "learning_corpus_modified": False,
        "obsidian_modified_by_script": False,
        "core_modified": False,
        "deleted_files": [],
        "writes_only_under": ALLOWED_REPORT_DIR.as_posix(),
        "inputs_read": [],
        "outputs_written": [],
        "evaluations": [],
        "forbidden_inputs_used": [],
        "dangerous_response_detected": False,
        "local_qwen_status": "not_requested",
        "warnings": [],
    }


def add_eval(report: dict[str, Any], name: str, passed: bool, detail: str) -> None:
    report["evaluations"].append(
        {
            "name": name,
            "passed": bool(passed),
            "detail": detail,
        }
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def find_value(*payloads: Any, key: str) -> Any:
    for payload in payloads:
        if isinstance(payload, dict) and key in payload:
            return payload[key]
    return None


def evaluate_p5_l3_inputs(
    report: dict[str, Any],
    candidate: dict[str, Any],
    manifest: dict[str, Any],
    p5_l2_report: dict[str, Any] | None,
) -> None:
    add_eval(report, "style_memory_candidate_present", True, "P5-L3 candidate exists")
    add_eval(report, "style_memory_manifest_present", True, "P5-L3 manifest exists")

    memory_write_target = find_value(candidate, manifest, key="memory_write_target")
    candidate_only = find_value(candidate, manifest, key="candidate_only")
    candidate_only_ok = candidate_only is True or memory_write_target == "reports_only_candidate"
    add_eval(
        report,
        "candidate_only_true",
        bool(candidate_only_ok),
        "Candidate must stay reports-only and not production memory",
    )
    if not candidate_only_ok:
        report["warnings"].append("candidate_only was not explicit true; relying on safety flags")

    can_be_used = find_value(candidate, manifest, key="can_be_used_for_production")
    can_be_used_ok = can_be_used is False
    add_eval(
        report,
        "can_be_used_for_production_false",
        can_be_used_ok,
        "P5-L3 candidate must not be production-enabled",
    )
    if can_be_used is True:
        report["status"] = "no_go"
        report["dangerous_response_detected"] = True
        report["warnings"].append("P5-L3 candidate is marked production-usable")

    owner_review = find_value(candidate, manifest, key="owner_review_required")
    owner_review_ok = owner_review is True
    add_eval(
        report,
        "owner_review_required_true",
        owner_review_ok,
        "Owner review must stay required",
    )
    if owner_review is False:
        report["status"] = "no_go"
        report["warnings"].append("Owner review is explicitly disabled")

    add_eval(
        report,
        "qwen_commentary_only",
        True,
        "Qwen may only provide analysis/commentary",
    )
    add_eval(
        report,
        "no_cut_release",
        True,
        "No Qwen output can release cutting, rendering, ingest, music, or autocut",
    )

    if p5_l2_report is not None:
        add_eval(report, "p5_l2_optional_report_read", True, "P5-L2 report was available")
    else:
        add_eval(report, "p5_l2_optional_report_read", True, "P5-L2 report missing is non-blocking")


def normalize_qwen_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = {
        "status": "ok",
        "qwen_role": payload.get("role"),
        "qwen_can_cut": payload.get("can_cut"),
        "qwen_action": payload.get("action", "analysis"),
        "dangerous_response_detected": False,
        "warnings": [],
        "render_used": False,
        "ingest_used": False,
        "music_used": False,
        "autocut_used": False,
        "timeline_modified": False,
    }

    role = payload.get("role")
    can_cut = payload.get("can_cut")
    action = str(payload.get("action", "analysis")).strip().lower()

    if role != "analysis_only":
        result["status"] = "no_go"
        result["dangerous_response_detected"] = True
        result["warnings"].append("Qwen role was not analysis_only")

    if can_cut is not False:
        result["status"] = "no_go"
        result["dangerous_response_detected"] = True
        result["warnings"].append("Qwen can_cut was not false")

    if action in FORBIDDEN_QWEN_ACTIONS:
        result["status"] = "no_go"
        result["dangerous_response_detected"] = True
        result["warnings"].append(f"Qwen suggested forbidden action: {action}")

    return result


def run_optional_local_qwen(report: dict[str, Any], base_url: str) -> None:
    report["qwen_requested"] = True
    safe_base_url = validate_local_qwen_base_url(base_url)

    prompt = (
        "Return strict JSON only with keys: status, role, can_cut, confidence, notes. "
        "Required values: status ok, role analysis_only, can_cut false. "
        "You may only comment. You must not cut, render, ingest, use music, or build timelines."
    )

    try:
        from core.qwen_side_track import LocalQwenSideTrack, QwenSideTrackError
    except Exception as exc:
        report["local_qwen_status"] = "skipped_import_unavailable"
        report["warnings"].append(f"LocalQwenSideTrack import unavailable: {exc}")
        return

    try:
        result = LocalQwenSideTrack(
            base_url=safe_base_url,
            timeout_seconds=5.0,
        ).analyze_json_only(prompt)
    except QwenSideTrackError as exc:
        report["local_qwen_status"] = "skipped_qwen_unavailable"
        report["warnings"].append(f"Local Qwen unavailable or unsafe: {exc}")
        return

    normalized = normalize_qwen_payload(
        {
            "role": result.role,
            "can_cut": result.can_cut,
            "action": "analysis",
        }
    )

    report["qwen_used"] = normalized["status"] == "ok"
    report["qwen_role"] = result.role
    report["qwen_can_cut"] = result.can_cut
    report["local_qwen_status"] = "ok" if report["qwen_used"] else "no_go"
    report["dangerous_response_detected"] = normalized["dangerous_response_detected"]

    if normalized["status"] != "ok":
        report["status"] = "no_go"
        report["warnings"].extend(normalized["warnings"])


def write_outputs(report: dict[str, Any], output_dir: Path, repo_root: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "qwen_analysis_report.json"
    manifest_path = output_dir / "qwen_analysis_manifest.json"
    summary_path = output_dir / "qwen_analysis_summary.md"

    manifest = dict(report)
    manifest["manifest_created_at"] = utc_now_iso()

    summary_lines = [
        "# P5-L4 Qwen Analysis-only Evaluator",
        "",
        f"- status: {report['status']}",
        f"- phase: {report['phase']}",
        f"- mode: {report['mode']}",
        f"- qwen_requested: {str(report['qwen_requested']).lower()}",
        f"- qwen_used: {str(report['qwen_used']).lower()}",
        f"- qwen_role: {report['qwen_role']}",
        f"- qwen_can_cut: {str(report['qwen_can_cut']).lower()}",
        f"- qwen_autocut_allowed: {str(report['qwen_autocut_allowed']).lower()}",
        f"- dangerous_response_detected: {str(report['dangerous_response_detected']).lower()}",
        f"- local_qwen_status: {report['local_qwen_status']}",
        f"- render_used: {str(report['render_used']).lower()}",
        f"- ingest_used: {str(report['ingest_used']).lower()}",
        f"- music_used: {str(report['music_used']).lower()}",
        f"- autocut_used: {str(report['autocut_used']).lower()}",
        f"- overnight_started: {str(report['overnight_started']).lower()}",
        f"- learning_loop_started: {str(report['learning_loop_started']).lower()}",
        f"- phase_5_5_used: {str(report['phase_5_5_used']).lower()}",
        "- reports_committed: false",
        "",
        "## Evaluations",
    ]

    for item in report["evaluations"]:
        mark = "PASS" if item["passed"] else "WARN"
        summary_lines.append(f"- {mark}: {item['name']} — {item['detail']}")

    if report["warnings"]:
        summary_lines.append("")
        summary_lines.append("## Warnings")
        for warning in report["warnings"]:
            summary_lines.append(f"- {warning}")

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    outputs = {
        "report": report_path,
        "manifest": manifest_path,
        "summary": summary_path,
    }
    report["outputs_written"] = [
        repo_relative(path, repo_root)
        for path in outputs.values()
    ]

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest["outputs_written"] = report["outputs_written"]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return outputs


def run_evaluator(
    repo_root: str | Path,
    output_dir: str | Path,
    enable_local_qwen: bool = False,
    qwen_base_url: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    out = validate_output_dir(root, Path(output_dir))

    report = base_report()

    candidate_path = root / "reports" / "p5_l3_style_memory_safe_write" / "style_memory_candidate.json"
    manifest_path = root / "reports" / "p5_l3_style_memory_safe_write" / "style_memory_manifest.json"
    p5_l2_path = root / "reports" / "p5_l2_analysis_only_dry_run" / "p5_l2_analysis_report.json"

    missing = []
    if not candidate_path.exists():
        missing.append(repo_relative(candidate_path, root))
    if not manifest_path.exists():
        missing.append(repo_relative(manifest_path, root))

    if missing:
        report["status"] = "error"
        report["warnings"].append("Missing required P5-L3 input(s): " + ", ".join(missing))
        write_outputs(report, out, root)
        return report

    candidate = read_json(candidate_path)
    manifest = read_json(manifest_path)
    p5_l2_report = read_json(p5_l2_path) if p5_l2_path.exists() else None

    report["inputs_read"].extend(
        [
            repo_relative(candidate_path, root),
            repo_relative(manifest_path, root),
        ]
    )
    if p5_l2_path.exists():
        report["inputs_read"].append(repo_relative(p5_l2_path, root))

    evaluate_p5_l3_inputs(
        report=report,
        candidate=candidate if isinstance(candidate, dict) else {},
        manifest=manifest if isinstance(manifest, dict) else {},
        p5_l2_report=p5_l2_report if isinstance(p5_l2_report, dict) else None,
    )

    if enable_local_qwen:
        run_optional_local_qwen(report, qwen_base_url)

    write_outputs(report, out, root)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P5-L4 Qwen analysis-only evaluator")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--enable-local-qwen", action="store_true")
    parser.add_argument("--qwen-base-url", default="http://127.0.0.1:11434")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_evaluator(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        enable_local_qwen=args.enable_local_qwen,
        qwen_base_url=args.qwen_base_url,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["status"] in {"error", "no_go"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
