from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any


def _word_to_dict(word: Any) -> dict[str, Any]:
    if isinstance(word, dict):
        return {
            "start": word.get("start"),
            "end": word.get("end"),
            "word": word.get("word", word.get("text")),
            "probability": word.get("probability"),
        }

    return {
        "start": getattr(word, "start", None),
        "end": getattr(word, "end", None),
        "word": getattr(word, "word", None) or getattr(word, "text", None),
        "probability": getattr(word, "probability", None),
    }


def _segment_to_dict(segment: Any) -> dict[str, Any]:
    if isinstance(segment, dict):
        raw_words = segment.get("words") or []
        return {
            "start": segment.get("start"),
            "end": segment.get("end"),
            "text": segment.get("text"),
            "confidence": segment.get("confidence"),
            "words": [_word_to_dict(word) for word in raw_words],
        }

    raw_words = getattr(segment, "words", None) or []
    return {
        "start": getattr(segment, "start", None),
        "end": getattr(segment, "end", None),
        "text": getattr(segment, "text", None),
        "confidence": getattr(segment, "confidence", None),
        "words": [_word_to_dict(word) for word in raw_words],
    }


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(message: str) -> None:
    print(f"[whisperx_bridge] {message}", flush=True)


def run_bridge(input_path: str, output_path: str, model_name: str) -> int:
    report_path = Path(output_path)
    try:
        _log(f"start input={input_path} model={model_name}")
        import whisperx

        _log("import_whisperx.done")
        audio_path = str(input_path)
        _log(f"model.load.start model={model_name} device=cuda compute_type=float16")
        model = whisperx.load_model(model_name, device="cuda", compute_type="float16")
        _log("model.load.done")
        _log("audio.load.start")
        audio = whisperx.load_audio(audio_path)
        _log("audio.load.done")
        _log("transcribe.start batch_size=16")
        result = model.transcribe(audio, batch_size=16)

        language = result.get("language")
        segments = list(result.get("segments") or [])
        _log(f"transcribe.done language={language} segment_count={len(segments)}")

        try:
            _log(f"align.load.start language={language} device=cuda")
            align_model, metadata = whisperx.load_align_model(
                language_code=language,
                device="cuda",
            )
            _log("align.load.done")
            _log("align.start")
            aligned = whisperx.align(
                segments,
                align_model,
                metadata,
                audio,
                device="cuda",
                return_char_alignments=False,
            )
            segments = list(aligned.get("segments") or segments)
            _log(f"align.done segment_count={len(segments)}")
        except Exception as align_exc:
            _log(f"align.failed {type(align_exc).__name__}: {align_exc}")
            _write_report(
                report_path,
                {
                    "status": "ok",
                    "engine": "whisperx",
                    "language": language,
                    "segments": [_segment_to_dict(segment) for segment in segments],
                    "warnings": [f"alignment_failed: {align_exc}"],
                },
            )
            return 0

        _log("write_report.ok")
        _write_report(
            report_path,
            {
                "status": "ok",
                "engine": "whisperx",
                "language": language,
                "segments": [_segment_to_dict(segment) for segment in segments],
                "warnings": [],
            },
        )
        return 0
    except Exception as exc:
        _log(f"error {type(exc).__name__}: {exc}")
        _write_report(
            report_path,
            {
                "status": "error",
                "engine": "whisperx",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Zenith WhisperX bridge worker")
    parser.add_argument("--input", required=True, help="Audio/video source path")
    parser.add_argument("--output", required=True, help="JSON report path")
    parser.add_argument("--model", default="base", help="WhisperX model name")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_bridge(
        input_path=args.input,
        output_path=args.output,
        model_name=args.model,
    )


if __name__ == "__main__":
    sys.exit(main())
