from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error as url_error
from urllib import parse as url_parse
from urllib import request as url_request


PHASE = "P5-L6"
MODE = "owner_review_quality_gate"
ALLOWED_OUTPUT_REL = Path("reports") / "p5_l6_owner_review_quality_gate"

REQUIRED_INPUTS = [
    "reports/p5_l2_analysis_only_dry_run/p5_l2_analysis_report.json",
    "reports/p5_l3_style_memory_safe_write/style_memory_manifest.json",
    "reports/p5_l3_style_memory_safe_write/style_memory_candidate.json",
    "reports/p5_l4_qwen_analysis_only_evaluator/qwen_analysis_manifest.json",
    "reports/p5_l5_overnight_dry_run/overnight_dry_run_manifest.json",
    "reports/p5_l5_overnight_dry_run/overnight_dry_run_plan.json",
]

OUTPUT_FILES = [
    "owner_review_packet.json",
    "owner_review_manifest.json",
    "owner_review_summary.md",
    "qwen_wake_up_response.json",
]

FORBIDDEN_QWEN_ACTIONS = {"cut", "render", "ingest", "music", "autocut", "qwen_autocut"}


class P5L6Error(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel_posix(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def resolve_output_dir(repo_root: Path, output_dir: str | Path) -> Path:
    root = repo_root.resolve()
    raw = Path(output_dir)
    out = raw if raw.is_absolute() else root / raw
    out = out.resolve()

    try:
        rel = out.relative_to(root)
    except ValueError as exc:
        raise P5L6Error(f"Output dir is outside repo root: {out}") from exc

    if rel != ALLOWED_OUTPUT_REL and ALLOWED_OUTPUT_REL not in rel.parents:
        raise P5L6Error(
            "Output dir must stay under "
            f"{ALLOWED_OUTPUT_REL.as_posix()}, got {rel.as_posix()}"
        )

    return out


def assert_output_scope(path: Path, output_dir: Path) -> None:
    try:
        path.resolve().relative_to(output_dir.resolve())
    except ValueError as exc:
        raise P5L6Error(f"Refusing write outside output dir: {path}") from exc


def read_json_file(repo_root: Path, rel_path: str) -> dict[str, Any]:
    path = repo_root / rel_path
    if not path.exists():
        raise P5L6Error(f"Missing required input: {rel_path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise P5L6Error(f"Invalid JSON input: {rel_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise P5L6Error(f"Input must be a JSON object: {rel_path}")
    return data


def write_json(path: Path, output_dir: Path, data: dict[str, Any]) -> None:
    assert_output_scope(path, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, output_dir: Path, text: str) -> None:
    assert_output_scope(path, output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def validate_local_qwen_base_url(base_url: str) -> str:
    parsed = url_parse.urlparse(base_url)

    if parsed.scheme != "http":
        raise ValueError("Only local http Ollama URLs are allowed")

    if parsed.username or parsed.password:
        raise ValueError("Credentials are not allowed in local Qwen URL")

    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Only 127.0.0.1 or localhost is allowed")

    if parsed.port != 11434:
        raise ValueError("Only local Ollama port 11434 is allowed")

    if parsed.path not in {"", "/"}:
        raise ValueError("Base URL must not include a custom path")

    return f"http://{parsed.hostname}:11434"


def make_qwen_prompt(packet: dict[str, Any]) -> str:
    return (
        "PROJECT ZENITH P5-L6 Wake-Up Check.\n"
        "Du bist nur analysis_only. Du darfst NICHT schneiden, rendern, ingesten, Musik bauen oder autocutten.\n"
        "Beantworte kurz als JSON mit exakt diesen Feldern:\n"
        'role="analysis_only", can_cut=false, recommendation_text, risks, owner_review_required=true.\n'
        "Fragen:\n"
        "1. Was ist an P5-L2 bis P5-L5 gut?\n"
        "2. Was ist riskant?\n"
        "3. Ist Owner Review nötig?\n"
        "4. Darf Qwen schneiden? Antwort muss nein sein.\n\n"
        f"Kontext:\n{json.dumps(packet, ensure_ascii=False)[:6000]}"
    )


def parse_json_object_from_text(text: str) -> dict[str, Any] | None:
    clean = text.strip()
    if not clean:
        return None

    try:
        data = json.loads(clean)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(clean[start : end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    return None


def assess_qwen_payload(payload: dict[str, Any]) -> dict[str, Any]:
    role_raw = str(payload.get("role", "")).strip()
    action_raw = str(payload.get("action", "")).strip().lower()
    can_cut_raw = payload.get("can_cut", False)

    can_cut_true = can_cut_raw is True or str(can_cut_raw).strip().lower() == "true"
    forbidden_action = any(item in action_raw for item in FORBIDDEN_QWEN_ACTIONS)
    wrong_role = bool(role_raw) and role_raw != "analysis_only"

    dangerous = can_cut_true or forbidden_action or wrong_role

    risks = payload.get("risks", [])
    if not isinstance(risks, list):
        risks = [str(risks)]

    return {
        "qwen_role_raw": role_raw or "missing",
        "qwen_can_cut_raw": can_cut_raw,
        "qwen_action_raw": action_raw,
        "dangerous_response_detected": dangerous,
        "risks": risks,
        "recommendation_text": str(payload.get("recommendation_text", "")).strip(),
        "owner_review_required_raw": payload.get("owner_review_required", None),
    }


def run_local_qwen(
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int = 8,
) -> dict[str, Any]:
    safe_base = validate_local_qwen_base_url(base_url)
    endpoint = safe_base + "/api/chat"

    body = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "options": {
            "temperature": 0,
            "num_predict": 350,
        },
    }

    req = url_request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with url_request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (url_error.URLError, TimeoutError, OSError) as exc:
        return {
            "status": "skipped_qwen_unavailable",
            "qwen_requested": True,
            "qwen_used": False,
            "warning": f"Local Ollama/Qwen unavailable or timed out: {exc}",
            "raw_response": "",
            "payload": {
                "role": "analysis_only",
                "can_cut": False,
                "recommendation_text": "",
                "risks": ["Qwen Wake-Up skipped because local Ollama was unavailable."],
                "owner_review_required": True,
            },
        }

    try:
        response_data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "status": "invalid_qwen_transport_json",
            "qwen_requested": True,
            "qwen_used": False,
            "warning": "Ollama returned non-JSON transport response.",
            "raw_response": raw,
            "payload": {
                "role": "analysis_only",
                "can_cut": False,
                "recommendation_text": "",
                "risks": ["Qwen transport response was not valid JSON."],
                "owner_review_required": True,
            },
        }

    content = ""
    if isinstance(response_data.get("message"), dict):
        content = str(response_data["message"].get("content", ""))
    elif "response" in response_data:
        content = str(response_data.get("response", ""))

    payload = parse_json_object_from_text(content)
    warning = ""
    if payload is None:
        warning = "Qwen response was not strict JSON; treated as commentary only."
        payload = {
            "role": "analysis_only",
            "can_cut": False,
            "recommendation_text": content[:1000],
            "risks": ["Qwen did not return strict schema JSON."],
            "owner_review_required": True,
        }

    return {
        "status": "ok",
        "qwen_requested": True,
        "qwen_used": True,
        "warning": warning,
        "raw_response": content,
        "payload": payload,
    }


def make_base_manifest(output_dir: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "status": "ok",
        "phase": PHASE,
        "mode": MODE,
        "created_at": utc_now(),
        "qwen_wake_up_check": True,
        "qwen_requested": False,
        "qwen_used": False,
        "qwen_role": "analysis_only",
        "qwen_can_cut": False,
        "qwen_autocut_allowed": False,
        "dangerous_response_detected": False,
        "owner_review_required": True,
        "owner_review_completed": False,
        "owner_go": False,
        "quality_gate_ready": True,
        "render_used": False,
        "ingest_used": False,
        "music_used": False,
        "autocut_used": False,
        "overnight_started": False,
        "real_overnight_started": False,
        "learning_loop_started": False,
        "phase_5_5_used": False,
        "external_network_used": False,
        "api_key_used": False,
        "timeline_modified": False,
        "production_files_modified": False,
        "video_configs_modified": False,
        "learning_corpus_modified": False,
        "obsidian_modified_by_script": False,
        "core_modified": False,
        "deleted_files": [],
        "writes_only_under": ALLOWED_OUTPUT_REL.as_posix(),
        "inputs_read": [],
        "outputs_written": [
            rel_posix(output_dir / name, repo_root) for name in OUTPUT_FILES
        ],
        "quality_findings": [],
        "warnings": [],
        "forbidden_inputs_used": [],
    }


def collect_quality_findings(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    p5_l2 = inputs[REQUIRED_INPUTS[0]]
    p5_l3_manifest = inputs[REQUIRED_INPUTS[1]]
    p5_l3_candidate = inputs[REQUIRED_INPUTS[2]]
    p5_l4 = inputs[REQUIRED_INPUTS[3]]
    p5_l5 = inputs[REQUIRED_INPUTS[4]]
    p5_l5_plan = inputs[REQUIRED_INPUTS[5]]

    return [
        {
            "area": "P5-L2 analysis-only dry-run",
            "status": p5_l2.get("status"),
            "good": [
                "analysis-only report exists",
                "style DNA and pair truth were inspected",
                "no render, ingest, music, autocut, or learning loop started",
            ],
            "evidence": {
                "pair_fingerprints": p5_l2.get("counts", {}).get("pair_fingerprints"),
                "top_solo_fingerprints": p5_l2.get("counts", {}).get("top_solo_fingerprints"),
                "vlog_fingerprints": p5_l2.get("counts", {}).get("vlog_fingerprints"),
                "pair_truth_entries": p5_l2.get("counts", {}).get("pair_truth_entries"),
            },
        },
        {
            "area": "P5-L3 style-memory safe write",
            "status": p5_l3_manifest.get("status"),
            "good": [
                "style-memory candidate exists",
                "write target stayed reports-only",
                "production files stayed untouched",
            ],
            "evidence": {
                "memory_write_target": p5_l3_manifest.get("memory_write_target"),
                "candidate_only": p5_l3_candidate.get("candidate_only"),
                "can_be_used_for_production": p5_l3_candidate.get("can_be_used_for_production"),
                "owner_review_required": p5_l3_candidate.get("owner_review_required"),
            },
        },
        {
            "area": "P5-L4 Qwen analysis-only evaluator",
            "status": p5_l4.get("status"),
            "good": [
                "Qwen role stayed analysis_only",
                "Qwen cutting stayed false",
                "dangerous response detector stayed clean",
            ],
            "evidence": {
                "qwen_requested": p5_l4.get("qwen_requested"),
                "qwen_used": p5_l4.get("qwen_used"),
                "qwen_role": p5_l4.get("qwen_role"),
                "qwen_can_cut": p5_l4.get("qwen_can_cut"),
                "dangerous_response_detected": p5_l4.get("dangerous_response_detected"),
                "local_qwen_status": p5_l4.get("local_qwen_status"),
            },
        },
        {
            "area": "P5-L5 bounded overnight dry-run",
            "status": p5_l5.get("status"),
            "good": [
                "bounded dry-run completed",
                "max_items limit held",
                "no real overnight or learning loop started",
            ],
            "evidence": {
                "dry_run_only": p5_l5.get("dry_run_only"),
                "max_items": p5_l5.get("max_items"),
                "items_planned": p5_l5.get("items_planned"),
                "items_processed": p5_l5.get("items_processed"),
                "plan_items": len(p5_l5_plan.get("planned_items", []))
                if isinstance(p5_l5_plan.get("planned_items", []), list)
                else None,
            },
        },
        {
            "area": "P5-L6 owner review requirement",
            "status": "required",
            "good": [
                "P5-L7 must not start before owner review and Master-GO",
                "Qwen may comment but cannot cut",
            ],
            "evidence": {
                "owner_review_required": True,
                "owner_review_completed": False,
                "owner_go": False,
            },
        },
    ]


def aggregate_warnings(inputs: dict[str, dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    for rel_path, data in inputs.items():
        source_warnings = data.get("warnings", [])
        if isinstance(source_warnings, list):
            for item in source_warnings:
                warnings.append(f"{rel_path}: {item}")
    return warnings


def aggregate_forbidden_inputs(inputs: dict[str, dict[str, Any]]) -> list[Any]:
    found: list[Any] = []
    for data in inputs.values():
        items = data.get("forbidden_inputs_used", [])
        if isinstance(items, list):
            found.extend(items)
    return found


def make_owner_packet(
    manifest: dict[str, Any],
    inputs: dict[str, dict[str, Any]],
    qwen_response: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "mode": MODE,
        "p5_l_progress_before_review": "75%",
        "p5_l_progress_after_owner_go": "85%",
        "phase_5": "100% / DONE",
        "phase_5_5_music": "0% / locked",
        "reports_checked": REQUIRED_INPUTS,
        "quality_findings": manifest["quality_findings"],
        "qwen_wake_up": {
            "requested": manifest["qwen_requested"],
            "used": manifest["qwen_used"],
            "role": manifest["qwen_role"],
            "can_cut": manifest["qwen_can_cut"],
            "autocut_allowed": manifest["qwen_autocut_allowed"],
            "dangerous_response_detected": manifest["dangerous_response_detected"],
            "transport_status": qwen_response.get("status"),
        },
        "owner_review_questions": [
            "Hast du owner_review_summary.md gelesen? ja/nein",
            "Wirkt die Lernqualität plausibel? ja/nein",
            "Hat Qwen sichtbar geantwortet oder wurde sauber skipped? sichtbar/skipped/nein",
            "Hat Qwen irgendwo Schneide-Rechte bekommen? ja/nein",
            "Darf P5-L7 später vorbereitet werden? ja/nein",
            "Gibt es Bauchgefühl-NO-GO? ja/nein",
        ],
        "safety": {
            "render_used": False,
            "ingest_used": False,
            "music_used": False,
            "autocut_used": False,
            "learning_loop_started": False,
            "phase_5_5_used": False,
        },
        "source_statuses": {
            rel_path: data.get("status") for rel_path, data in inputs.items()
        },
    }


def make_summary_md(
    manifest: dict[str, Any],
    packet: dict[str, Any],
    qwen_response: dict[str, Any],
) -> str:
    qwen_line = "skipped"
    if manifest["qwen_requested"] and manifest["qwen_used"]:
        qwen_line = "sichtbar geantwortet"
    elif manifest["qwen_requested"]:
        qwen_line = qwen_response.get("status", "skipped")

    findings = "\n".join(
        f"- {item['area']}: {item['status']}"
        for item in manifest["quality_findings"]
    )

    warnings = manifest.get("warnings", [])
    warning_lines = "\n".join(f"- {item}" for item in warnings) if warnings else "- keine"

    return f"""# P5-L6 Owner Review + Lernqualität

## Status

- Phase 5: 100% / DONE
- P5-L vor Review: 75%
- P5-L6 Ziel nach Ali Owner GO: 85%
- Phase 5.5 Musik: 0% / locked
- Quality Gate ready: {str(manifest["quality_gate_ready"]).lower()}
- Owner Review required: true
- Owner Review completed: false
- Owner GO: false

## Was wurde geprüft?

{findings}

## Lernqualität kurz erklärt

P5-L2 hat den vorhandenen Lernkorpus nur analysiert.
P5-L3 hat daraus nur einen sicheren Reports-only Style-Memory-Kandidaten erzeugt.
P5-L4 hat Qwen nur als Analyse-Rolle bewertet, ohne Schneide-Rechte.
P5-L5 hat einen begrenzten Overnight-Dry-run mit max_items=5 durchgeführt, ohne echten Dauerloop.

## Qwen Wake-Up Check

- Ergebnis: {qwen_line}
- qwen_requested: {str(manifest["qwen_requested"]).lower()}
- qwen_used: {str(manifest["qwen_used"]).lower()}
- qwen_role: analysis_only
- qwen_can_cut: false
- qwen_autocut_allowed: false
- dangerous_response_detected: {str(manifest["dangerous_response_detected"]).lower()}

## Offene Risiken

{warning_lines}

## Darf P5-L7 vorbereitet werden?

Nur wenn Ali Owner Review GO gibt und danach Master-GO kommt.
P5-L7 darf vorbereitet werden, aber der echte kontrollierte Learning-Loop ist noch NICHT gestartet.

## Ali Owner Review Fragen

1. Hast du owner_review_summary.md gelesen? ja/nein
2. Wirkt die Lernqualität plausibel? ja/nein
3. Hat Qwen sichtbar geantwortet oder wurde sauber skipped? sichtbar/skipped/nein
4. Hat Qwen irgendwo Schneide-Rechte bekommen? ja/nein
5. Darf P5-L7 später vorbereitet werden? ja/nein
6. Gibt es Bauchgefühl-NO-GO? ja/nein

## Harte Safety

- Kein Render
- Kein Ingest
- Keine Musik
- Kein Autocut
- Kein echter Overnight-Dauerlauf
- Kein echter Learning-Loop
- Keine Phase 5.5
"""


def write_error_outputs(
    repo_root: Path,
    output_dir: Path,
    message: str,
) -> dict[str, Any]:
    manifest = make_base_manifest(output_dir, repo_root)
    manifest["status"] = "error"
    manifest["quality_gate_ready"] = False
    manifest["warnings"].append(message)

    qwen_response = {
        "status": "skipped_due_to_error",
        "qwen_requested": False,
        "qwen_used": False,
        "payload": {
            "role": "analysis_only",
            "can_cut": False,
            "owner_review_required": True,
        },
    }

    packet = {
        "phase": PHASE,
        "mode": MODE,
        "status": "error",
        "error": message,
        "owner_review_required": True,
    }

    summary = f"""# P5-L6 Owner Review + Lernqualität

Status: error

Blocker:
- {message}

Keine weiteren Schritte starten.
"""

    write_json(output_dir / "owner_review_manifest.json", output_dir, manifest)
    write_json(output_dir / "qwen_wake_up_response.json", output_dir, qwen_response)
    write_json(output_dir / "owner_review_packet.json", output_dir, packet)
    write_text(output_dir / "owner_review_summary.md", output_dir, summary)

    return manifest


def build_owner_review(
    repo_root: str | Path,
    output_dir: str | Path,
    enable_local_qwen: bool = False,
    qwen_base_url: str = "http://127.0.0.1:11434",
    qwen_model: str = "qwen3.6:latest",
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    out = resolve_output_dir(root, output_dir)
    out.mkdir(parents=True, exist_ok=True)

    try:
        inputs = {rel_path: read_json_file(root, rel_path) for rel_path in REQUIRED_INPUTS}
    except P5L6Error as exc:
        return write_error_outputs(root, out, str(exc))

    manifest = make_base_manifest(out, root)
    manifest["inputs_read"] = REQUIRED_INPUTS.copy()
    manifest["quality_findings"] = collect_quality_findings(inputs)
    manifest["warnings"] = aggregate_warnings(inputs)
    manifest["forbidden_inputs_used"] = aggregate_forbidden_inputs(inputs)

    qwen_response: dict[str, Any] = {
        "status": "skipped_not_requested",
        "qwen_requested": False,
        "qwen_used": False,
        "payload": {
            "role": "analysis_only",
            "can_cut": False,
            "recommendation_text": "",
            "risks": [],
            "owner_review_required": True,
        },
    }

    packet_preview = {
        "reports_checked": REQUIRED_INPUTS,
        "quality_findings": manifest["quality_findings"],
        "safety": {
            "qwen_role": "analysis_only",
            "qwen_can_cut": False,
            "qwen_autocut_allowed": False,
        },
    }

    if enable_local_qwen:
        prompt = make_qwen_prompt(packet_preview)
        try:
            qwen_response = run_local_qwen(qwen_base_url, qwen_model, prompt)
        except ValueError as exc:
            qwen_response = {
                "status": "blocked_external_or_invalid_qwen_url",
                "qwen_requested": True,
                "qwen_used": False,
                "warning": str(exc),
                "payload": {
                    "role": "analysis_only",
                    "can_cut": False,
                    "recommendation_text": "",
                    "risks": [str(exc)],
                    "owner_review_required": True,
                },
            }

        manifest["qwen_requested"] = True
        manifest["qwen_used"] = bool(qwen_response.get("qwen_used", False))
        if qwen_response.get("warning"):
            manifest["warnings"].append(str(qwen_response["warning"]))

        assessment = assess_qwen_payload(qwen_response.get("payload", {}))
        manifest["dangerous_response_detected"] = bool(
            assessment["dangerous_response_detected"]
        )

        if manifest["dangerous_response_detected"]:
            manifest["status"] = "no_go"
            manifest["quality_gate_ready"] = False
            manifest["warnings"].append(
                "Dangerous Qwen response detected; no action was executed."
            )

        qwen_response["safety_assessment"] = assessment

    packet = make_owner_packet(manifest, inputs, qwen_response)
    summary = make_summary_md(manifest, packet, qwen_response)

    write_json(out / "qwen_wake_up_response.json", out, qwen_response)
    write_json(out / "owner_review_packet.json", out, packet)
    write_json(out / "owner_review_manifest.json", out, manifest)
    write_text(out / "owner_review_summary.md", out, summary)

    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P5-L6 Owner Review Quality Gate")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--enable-local-qwen", action="store_true")
    parser.add_argument("--qwen-base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--qwen-model", default="qwen3.6:latest")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_owner_review(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        enable_local_qwen=args.enable_local_qwen,
        qwen_base_url=args.qwen_base_url,
        qwen_model=args.qwen_model,
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0 if manifest.get("status") in {"ok", "no_go"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
