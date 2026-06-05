from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


PHASE = "P5-L6.5"
GROUP = "5D"
MODE = "qwen_control_run"
ALLOWED_OUTPUT_REL = Path("reports") / "p5_l65_qwen_control_run"
ALLOWED_LOCAL_HOSTS = {"127.0.0.1", "localhost"}
ALLOWED_QWEN_ACTIONS = {"analyze", "comment", "review"}
FORBIDDEN_QWEN_ACTIONS = {"cut", "render", "ingest", "music", "autocut", "timeline"}


class P5L65QwenControlError(RuntimeError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def ensure_repo_root_on_sys_path(repo_root: Path) -> None:
    root_text = str(repo_root.resolve())
    if root_text not in sys.path:
        sys.path.insert(0, root_text)


def validate_output_dir(repo_root: Path, output_dir: Path) -> Path:
    root = repo_root.resolve()
    out = output_dir if output_dir.is_absolute() else root / output_dir
    out = out.resolve()

    try:
        rel = out.relative_to(root)
    except ValueError as exc:
        raise ValueError("output-dir must be inside repo-root") from exc

    if rel.as_posix() != ALLOWED_OUTPUT_REL.as_posix():
        raise ValueError("output-dir must be exactly reports/p5_l65_qwen_control_run")

    return out


def validate_local_base_url(base_url: str) -> str:
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("base_url must be a non-empty string")

    cleaned = base_url.strip().rstrip("/")
    parsed = urlparse(cleaned)

    if parsed.scheme != "http":
        raise ValueError("base_url must use local http only")

    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_LOCAL_HOSTS:
        raise ValueError("base_url must point to localhost or 127.0.0.1")

    if parsed.username or parsed.password:
        raise ValueError("base_url must not contain credentials")

    if parsed.path not in ("", "/"):
        raise ValueError("base_url must not contain a path")

    return cleaned


def make_prompt() -> str:
    return (
        "Du bist Qwen im PROJECT ZENITH Kontrollrun.\n"
        "Du bist NUR analysis_only.\n"
        "Du darfst NICHT schneiden.\n"
        "Du darfst NICHT rendern.\n"
        "Du darfst NICHT ingesten.\n"
        "Du darfst NICHT Musik nutzen.\n"
        "Du darfst NICHT Autocut ausloesen.\n"
        "Du darfst NICHT Timeline aendern.\n\n"
        "Antworte NUR als JSON. Pflichtwerte:\n"
        "{\n"
        '  "status": "ok",\n'
        '  "role": "analysis_only",\n'
        '  "can_cut": false,\n'
        '  "confidence": 0.0,\n'
        '  "notes": ["kurzer sicherheitshinweis"],\n'
        '  "action": "analyze",\n'
        '  "summary": "kurze sichtbare antwort",\n'
        '  "risks": ["kurzes risiko oder none"],\n'
        '  "recommendation": "kurze empfehlung",\n'
        '  "owner_review_required": true\n'
        "}\n"
    )


def base_manifest(
    output_dir: Path,
    repo_root: Path,
    model: str = "",
    base_url: str = "http://127.0.0.1:11434",
) -> dict[str, Any]:
    outputs = [
        output_dir / "qwen_control_manifest.json",
        output_dir / "qwen_control_response.json",
        output_dir / "qwen_control_summary.md",
    ]

    return {
        "status": "planned_without_qwen",
        "phase": PHASE,
        "group": GROUP,
        "mode": MODE,
        "created_at": utc_now_iso(),
        "qwen_requested": False,
        "qwen_used": False,
        "qwen_visible_response": False,
        "qwen_model": model,
        "base_url": base_url,
        "qwen_role": "analysis_only",
        "qwen_can_cut": False,
        "qwen_autocut_allowed": False,
        "dangerous_response_detected": False,
        "owner_review_required": True,
        "render_used": False,
        "ingest_used": False,
        "music_used": False,
        "autocut_used": False,
        "timeline_modified": False,
        "learning_loop_started": False,
        "overnight_started": False,
        "real_overnight_started": False,
        "phase_5_5_used": False,
        "external_network_used": False,
        "api_key_used": False,
        "production_files_modified": False,
        "video_configs_modified": False,
        "learning_corpus_modified": False,
        "obsidian_modified_by_script": False,
        "core_modified": False,
        "deleted_files": [],
        "writes_only_under": ALLOWED_OUTPUT_REL.as_posix(),
        "inputs_read": [],
        "outputs_written": [repo_relative(path, repo_root) for path in outputs],
        "warnings": [],
        "forbidden_inputs_used": [],
    }


def parse_json_object(text: str) -> dict[str, Any] | None:
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


def normalize_qwen_payload(payload: dict[str, Any]) -> dict[str, Any]:
    role = str(payload.get("role", "")).strip()
    action = str(payload.get("action", "")).strip().lower()
    can_cut = payload.get("can_cut")
    owner_review_required = payload.get("owner_review_required")

    warnings: list[str] = []
    dangerous = False

    if role != "analysis_only":
        dangerous = True
        warnings.append("Qwen role was not analysis_only")

    if can_cut is not False:
        dangerous = True
        warnings.append("Qwen can_cut was not false")

    if action not in ALLOWED_QWEN_ACTIONS:
        dangerous = True
        warnings.append("Qwen action was not allowed")

    if any(forbidden in action for forbidden in FORBIDDEN_QWEN_ACTIONS):
        dangerous = True
        warnings.append(f"Qwen suggested forbidden action: {action}")

    if owner_review_required is not True:
        warnings.append("owner_review_required was not true")

    risks = payload.get("risks", [])
    if not isinstance(risks, list):
        risks = [str(risks)]

    return {
        "status": "no_go" if dangerous else "ok",
        "qwen_role": role or "missing",
        "qwen_can_cut": can_cut,
        "qwen_action": action or "missing",
        "summary": str(payload.get("summary", "")).strip(),
        "risks": [str(item) for item in risks],
        "recommendation": str(payload.get("recommendation", "")).strip(),
        "owner_review_required": owner_review_required,
        "dangerous_response_detected": dangerous,
        "warnings": warnings,
        "raw_payload": payload,
    }


def apply_normalized_response(
    manifest: dict[str, Any],
    response: dict[str, Any],
    normalized: dict[str, Any],
) -> None:
    visible = bool(normalized["summary"] or normalized["recommendation"] or normalized["risks"])

    manifest["status"] = normalized["status"]
    manifest["qwen_used"] = normalized["status"] == "ok" and visible
    manifest["qwen_visible_response"] = normalized["status"] == "ok" and visible
    manifest["qwen_role"] = normalized["qwen_role"]
    manifest["qwen_can_cut"] = normalized["qwen_can_cut"]
    manifest["dangerous_response_detected"] = normalized["dangerous_response_detected"]
    manifest["owner_review_required"] = normalized["owner_review_required"] is True
    manifest["warnings"].extend(normalized["warnings"])

    response["normalized"] = normalized


def run_local_qwen_control(
    repo_root: Path,
    manifest: dict[str, Any],
    model: str,
    base_url: str,
    timeout_sec: float,
) -> dict[str, Any]:
    safe_base_url = validate_local_base_url(base_url)
    ensure_repo_root_on_sys_path(repo_root)

    manifest["qwen_requested"] = True
    manifest["qwen_model"] = model
    manifest["base_url"] = safe_base_url

    try:
        from core.qwen_side_track import LocalQwenSideTrack, QwenSideTrackError
    except Exception as exc:
        manifest["status"] = "no_go"
        manifest["warnings"].append(f"LocalQwenSideTrack import unavailable: {exc}")
        return {
            "status": "import_unavailable",
            "visible_response": False,
            "raw_text": "",
            "payload": {},
        }

    try:
        result = LocalQwenSideTrack(
            model=model,
            base_url=safe_base_url,
            timeout_seconds=timeout_sec,
        ).analyze_json_only(make_prompt())
    except QwenSideTrackError as exc:
        message = str(exc)
        manifest["status"] = "qwen_timeout" if "timed out" in message.lower() else "no_go"
        manifest["warnings"].append(f"Local Qwen unavailable or unsafe: {message}")
        return {
            "status": manifest["status"],
            "visible_response": False,
            "raw_text": "",
            "payload": {},
            "error": message,
        }

    payload = parse_json_object(result.raw_text)
    if payload is None:
        manifest["status"] = "no_go"
        manifest["warnings"].append("Qwen response was not valid JSON")
        return {
            "status": "invalid_json",
            "visible_response": False,
            "raw_text": result.raw_text,
            "payload": {},
        }

    normalized = normalize_qwen_payload(payload)
    response = {
        "status": normalized["status"],
        "visible_response": True,
        "raw_text": result.raw_text,
        "payload": payload,
        "adapter_result": {
            "status": result.status,
            "role": result.role,
            "can_cut": result.can_cut,
            "confidence": result.confidence,
            "notes": result.notes,
        },
    }
    apply_normalized_response(manifest, response, normalized)
    return response


def build_summary(manifest: dict[str, Any], response: dict[str, Any]) -> str:
    normalized = response.get("normalized", {})
    risks = normalized.get("risks", [])
    risk_lines = "\n".join(f"- {item}" for item in risks) if risks else "- none"

    return "\n".join(
        [
            "# P5-L6.5 5D Qwen Control Run",
            "",
            f"- status: {manifest['status']}",
            f"- qwen_requested: {str(manifest['qwen_requested']).lower()}",
            f"- qwen_used: {str(manifest['qwen_used']).lower()}",
            f"- qwen_visible_response: {str(manifest['qwen_visible_response']).lower()}",
            f"- qwen_model: {manifest['qwen_model']}",
            f"- base_url: {manifest['base_url']}",
            f"- qwen_role: {manifest['qwen_role']}",
            f"- qwen_can_cut: {str(manifest['qwen_can_cut']).lower()}",
            f"- qwen_autocut_allowed: {str(manifest['qwen_autocut_allowed']).lower()}",
            f"- dangerous_response_detected: {str(manifest['dangerous_response_detected']).lower()}",
            f"- render_used: {str(manifest['render_used']).lower()}",
            f"- ingest_used: {str(manifest['ingest_used']).lower()}",
            f"- music_used: {str(manifest['music_used']).lower()}",
            f"- autocut_used: {str(manifest['autocut_used']).lower()}",
            f"- learning_loop_started: {str(manifest['learning_loop_started']).lower()}",
            f"- phase_5_5_used: {str(manifest['phase_5_5_used']).lower()}",
            "",
            "## Qwen Response",
            "",
            f"- summary: {normalized.get('summary', '')}",
            f"- recommendation: {normalized.get('recommendation', '')}",
            "",
            "## Risks",
            "",
            risk_lines,
            "",
        ]
    )


def write_outputs(
    output_dir: Path,
    manifest: dict[str, Any],
    response: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "qwen_control_response.json").write_text(
        json.dumps(response, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "qwen_control_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "qwen_control_summary.md").write_text(
        build_summary(manifest, response),
        encoding="utf-8",
    )


def run_control(
    repo_root: str | Path,
    output_dir: str | Path,
    enable_local_qwen: bool = False,
    model: str = "",
    base_url: str = "http://127.0.0.1:11434",
    timeout_sec: float = 120,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    out = validate_output_dir(root, Path(output_dir))
    safe_base_url = validate_local_base_url(base_url)

    manifest = base_manifest(out, root, model=model, base_url=safe_base_url)
    response: dict[str, Any] = {
        "status": "planned_without_qwen",
        "visible_response": False,
        "payload": {},
        "raw_text": "",
    }

    if enable_local_qwen:
        if not model.strip():
            raise ValueError("model must be provided when --enable-local-qwen is used")
        response = run_local_qwen_control(
            repo_root=root,
            manifest=manifest,
            model=model.strip(),
            base_url=safe_base_url,
            timeout_sec=timeout_sec,
        )

    write_outputs(out, manifest, response)
    return {
        "manifest": manifest,
        "response": response,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="P5-L6.5 5D Qwen control run")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--enable-local-qwen", action="store_true")
    parser.add_argument("--model", default="")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout-sec", type=float, default=120.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_control(
        repo_root=args.repo_root,
        output_dir=args.output_dir,
        enable_local_qwen=args.enable_local_qwen,
        model=args.model,
        base_url=args.base_url,
        timeout_sec=args.timeout_sec,
    )
    print(json.dumps(result["manifest"], indent=2, ensure_ascii=False))
    return 0 if result["manifest"]["status"] in {"ok", "planned_without_qwen"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
