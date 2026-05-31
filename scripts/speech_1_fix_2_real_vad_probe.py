from __future__ import annotations

import argparse
import array
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.real_vad_validation import (
    invert_regions_to_silence_gaps,
    merge_regions,
    total_duration,
    validate_real_vad_windows,
)


DEFAULT_SAMPLE_RATE = 16000


def _tool_path(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    candidate = Path("D:/Tools/ffmpeg/bin") / f"{name}.exe"
    if candidate.exists():
        return str(candidate)
    return name


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _media_duration_from_speech_report(path: Path) -> float | None:
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line.startswith("media_duration_seconds="):
            return float(line.split("=", 1)[1].strip())
    return None


def _probe_duration(video_path: Path) -> float:
    cmd = [
        _tool_path("ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nokey=1:noprint_wrappers=1",
        str(video_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {proc.stderr}")
    return max(0.0, float(proc.stdout.strip()))


def _extract_mic_wav(
    *,
    video_path: Path,
    mic_track_1based: int,
    sample_rate: int,
    out_wav: Path,
) -> None:
    stream_index = max(0, int(mic_track_1based) - 1)

    cmd = [
        _tool_path("ffmpeg"),
        "-y",
        "-v",
        "error",
        "-i",
        str(video_path),
        "-map",
        f"0:a:{stream_index}",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-acodec",
        "pcm_s16le",
        str(out_wav),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg mic wav extract failed for 0:a:{stream_index}: {proc.stderr}")



def _load_wav_as_torch_tensor(
    *,
    wav_path: Path,
    expected_sample_rate: int,
):
    import torch  # type: ignore

    with wave.open(str(wav_path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frame_count = wf.getnframes()
        raw = wf.readframes(frame_count)

    if sample_width != 2:
        raise RuntimeError(f"expected 16-bit PCM wav, got sample_width={sample_width}")
    if sample_rate != expected_sample_rate:
        raise RuntimeError(f"expected sample_rate={expected_sample_rate}, got {sample_rate}")

    samples = array.array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()

    if channels > 1:
        samples = array.array("h", samples[0::channels])

    waveform = torch.tensor(samples, dtype=torch.float32) / 32768.0
    return waveform.contiguous()


def _run_silero_vad(
    *,
    wav_path: Path,
    sample_rate: int,
    media_duration_seconds: float,
    threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    import torch  # type: ignore

    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=False,
        trust_repo=True,
    )
    get_speech_timestamps = utils[0]

    # Wichtig:
    # Nicht utils.read_audio benutzen, weil das lokal am torchaudio-Backend scheitern kann.
    # Wir laden die WAV selbst und geben Silero direkt einen Torch-Tensor.
    wav = _load_wav_as_torch_tensor(
        wav_path=wav_path,
        expected_sample_rate=sample_rate,
    )

    timestamps = get_speech_timestamps(
        wav,
        model,
        sampling_rate=sample_rate,
        threshold=float(threshold),
        min_speech_duration_ms=180,
        min_silence_duration_ms=180,
        speech_pad_ms=100,
    )

    regions: list[dict[str, Any]] = []
    for index, item in enumerate(timestamps, start=1):
        start = round(float(item["start"]) / sample_rate, 3)
        end = round(float(item["end"]) / sample_rate, 3)
        if end <= start:
            continue
        regions.append({
            "speech_region_id": f"real_vad_speech_{index:04d}",
            "start_seconds": start,
            "end_seconds": min(round(media_duration_seconds, 3), end),
            "duration_seconds": round(max(0.0, end - start), 3),
            "source": "silero_vad_torchhub_tensor_input",
        })

    return merge_regions(
        regions,
        max_gap_seconds=0.20,
        min_region_seconds=0.15,
        source="silero_vad_torchhub_tensor_input",
    ), {
        "engine": "silero_vad_torchhub_tensor_input",
        "threshold": threshold,
        "sample_rate": sample_rate,
        "speech_region_count_raw": len(timestamps),
        "audio_input": "manual_wave_pcm_to_torch_tensor",
    }


def _run_pyannote_pipeline_vad(
    *,
    wav_path: Path,
    sample_rate: int,
    media_duration_seconds: float,
    hf_token: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from pyannote.audio import Pipeline  # type: ignore

    last_error: Exception | None = None
    pipeline = None

    # Pyannote-Versionen unterscheiden sich:
    # neue Versionen: token=
    # alte Versionen: use_auth_token=
    # manche lokalen Modelle: ohne Token
    for kwargs in (
        {"token": hf_token} if hf_token else {},
        {"use_auth_token": hf_token} if hf_token else {},
        {},
    ):
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/voice-activity-detection",
                **kwargs,
            )
            break
        except Exception as exc:
            last_error = exc

    if pipeline is None:
        raise RuntimeError(f"pyannote pipeline unavailable: {type(last_error).__name__}: {last_error}")

    waveform = _load_wav_as_torch_tensor(
        wav_path=wav_path,
        expected_sample_rate=sample_rate,
    ).unsqueeze(0)

    # TorchCodec umgehen: Audio wird vorab als Tensor ?bergeben.
    output = pipeline({
        "waveform": waveform,
        "sample_rate": sample_rate,
    })

    regions: list[dict[str, Any]] = []
    for index, segment in enumerate(output.get_timeline().support(), start=1):
        start = round(float(segment.start), 3)
        end = min(round(media_duration_seconds, 3), round(float(segment.end), 3))
        if end <= start:
            continue
        regions.append({
            "speech_region_id": f"real_vad_speech_{index:04d}",
            "start_seconds": start,
            "end_seconds": end,
            "duration_seconds": round(max(0.0, end - start), 3),
            "source": "pyannote_voice_activity_detection_tensor_input",
        })

    return merge_regions(
        regions,
        max_gap_seconds=0.20,
        min_region_seconds=0.15,
        source="pyannote_voice_activity_detection_tensor_input",
    ), {
        "engine": "pyannote_voice_activity_detection_tensor_input",
        "sample_rate": sample_rate,
        "speech_region_count_raw": len(regions),
        "hf_token_used": bool(hf_token),
        "audio_input": "manual_wave_pcm_to_torch_tensor",
    }


def _run_real_vad_auto(
    *,
    wav_path: Path,
    sample_rate: int,
    media_duration_seconds: float,
    engine: str,
    hf_token: str | None,
    silero_threshold: float,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []

    if engine in {"auto", "pyannote"}:
        try:
            regions, metadata = _run_pyannote_pipeline_vad(
                wav_path=wav_path,
                sample_rate=sample_rate,
                media_duration_seconds=media_duration_seconds,
                hf_token=hf_token,
            )
            attempts.append({"engine": "pyannote_voice_activity_detection", "status": "PASS"})
            return regions, metadata, attempts
        except Exception as exc:
            attempts.append({
                "engine": "pyannote_voice_activity_detection",
                "status": "FAIL",
                "error": f"{type(exc).__name__}: {exc}",
            })
            if engine == "pyannote":
                raise

    if engine in {"auto", "silero"}:
        try:
            regions, metadata = _run_silero_vad(
                wav_path=wav_path,
                sample_rate=sample_rate,
                media_duration_seconds=media_duration_seconds,
                threshold=silero_threshold,
            )
            attempts.append({"engine": "silero_vad_torchhub", "status": "PASS"})
            return regions, metadata, attempts
        except Exception as exc:
            attempts.append({
                "engine": "silero_vad_torchhub",
                "status": "FAIL",
                "error": f"{type(exc).__name__}: {exc}",
            })
            if engine == "silero":
                raise

    raise RuntimeError(
        "No real trained VAD available. Energy fallback is disabled. Attempts: "
        + json.dumps(attempts, ensure_ascii=False)
    )


def _write_report(
    *,
    report_path: Path,
    video_path: Path,
    mic_track_1based: int,
    media_duration_seconds: float,
    vad_metadata: dict[str, Any],
    attempts: list[dict[str, Any]],
    speech_regions_path: Path,
    silence_gaps_path: Path,
    validation_path: Path,
    speech_regions: list[Mapping[str, Any]],
    silence_gaps: list[Mapping[str, Any]],
    validation: dict[str, Any],
) -> None:
    speech_seconds = total_duration(list(speech_regions))
    silence_seconds = total_duration(list(silence_gaps))

    lines: list[str] = []
    lines.append("PROJECT ZENITH - SPEECH-1-FIX-2 REAL TRAINED VAD REPORT")
    lines.append("")
    lines.append(f"video={video_path}")
    lines.append(f"mic_track_1based={mic_track_1based}")
    lines.append(f"media_duration_seconds={round(media_duration_seconds, 3)}")
    lines.append("")
    lines.append("ENGINE")
    for key, value in vad_metadata.items():
        lines.append(f"- {key}: {value}")
    lines.append("- energy_fallback_used: False")
    lines.append("")
    lines.append("ENGINE ATTEMPTS")
    for item in attempts:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("OUTPUTS")
    lines.append(f"- real_vad_speech_regions={speech_regions_path}")
    lines.append(f"- real_vad_silence_gaps={silence_gaps_path}")
    lines.append(f"- real_vad_validation={validation_path}")
    lines.append(f"- report={report_path}")
    lines.append("")
    lines.append("SPEECH / SILENCE SUMMARY")
    lines.append(f"- speech_region_count={len(speech_regions)}")
    lines.append(f"- silence_gap_count={len(silence_gaps)}")
    lines.append(f"- speech_seconds={speech_seconds}")
    lines.append(f"- silence_seconds={silence_seconds}")
    lines.append(f"- speech_share_percent={validation.get('speech_share_percent')}")
    lines.append(f"- speech_share_expected_range_percent={validation.get('speech_share_expected_range_percent')}")
    lines.append(f"- speech_share_status={validation.get('speech_share_status')}")
    lines.append("")
    lines.append("KNOWN SPEECH VALIDATION")
    for check in validation.get("known_speech_checks", []):
        lines.append(
            f"- {check.get('status')} {check.get('name')} "
            f"range={check.get('range_seconds')} "
            f"speech_overlap={check.get('speech_overlap_seconds')} "
            f"min={check.get('min_required_seconds')}"
        )
    lines.append("")
    lines.append("KNOWN SILENCE VALIDATION")
    for check in validation.get("known_silence_checks", []):
        lines.append(
            f"- {check.get('status')} {check.get('name')} "
            f"range={check.get('range_seconds')} "
            f"silence_overlap={check.get('silence_overlap_seconds')} "
            f"min={check.get('min_required_seconds')}"
        )
    lines.append("")
    lines.append("VERDICT")
    lines.append(f"- overall_status={validation.get('overall_status')}")
    lines.append(f"- failed_count={validation.get('failed_count')}")
    if validation.get("overall_status") != "PASS":
        lines.append("- NO_GO_REASON=real VAD ran, but plausibility validation failed")
    else:
        lines.append("- GO_REASON=real trained VAD ran and plausibility validation passed")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default=r"D:\Zenith\inbox\gaming_main\Fortnite Full Video.mp4")
    parser.add_argument("--mic-track", type=int, default=1)
    parser.add_argument("--speech-report", default="reports/speech_1_transcript/speech_1_report.txt")
    parser.add_argument("--out-dir", default="reports/speech_1_fix_vad")
    parser.add_argument("--engine", choices=["auto", "pyannote", "silero"], default="auto")
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--silero-threshold", type=float, default=0.30)
    parser.add_argument("--hf-token-env", default="HF_TOKEN")
    args = parser.parse_args(argv)

    video_path = Path(args.video)
    speech_report_path = Path(args.speech_report)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"video not found: {video_path}")

    media_duration = _media_duration_from_speech_report(speech_report_path)
    if media_duration is None:
        media_duration = _probe_duration(video_path)

    hf_token = os.environ.get(args.hf_token_env) or os.environ.get("HUGGINGFACE_TOKEN")

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / "fortnite_mic_stream_1.wav"

        print("[SPEECH-1-FIX-2] extracting mic stream to wav...")
        _extract_mic_wav(
            video_path=video_path,
            mic_track_1based=args.mic_track,
            sample_rate=args.sample_rate,
            out_wav=wav_path,
        )

        print("[SPEECH-1-FIX-2] running real trained VAD...")
        speech_regions, vad_metadata, attempts = _run_real_vad_auto(
            wav_path=wav_path,
            sample_rate=args.sample_rate,
            media_duration_seconds=float(media_duration),
            engine=args.engine,
            hf_token=hf_token,
            silero_threshold=args.silero_threshold,
        )

    silence_gaps = invert_regions_to_silence_gaps(
        speech_regions,
        media_duration_seconds=float(media_duration),
        min_silence_seconds=0.05,
        source=f"{vad_metadata.get('engine')}_silence",
    )

    validation = validate_real_vad_windows(
        speech_regions=speech_regions,
        silence_gaps=silence_gaps,
        media_duration_seconds=float(media_duration),
    )

    speech_regions_path = out_dir / "real_vad_fortnite_speech_regions.json"
    silence_gaps_path = out_dir / "real_vad_fortnite_silence_gaps.json"
    validation_path = out_dir / "real_vad_validation.json"
    report_path = out_dir / "speech_1_fix_2_real_vad_report.txt"

    _write_json(speech_regions_path, {
        "engine": vad_metadata.get("engine"),
        "metadata": vad_metadata,
        "media_duration_seconds": round(float(media_duration), 3),
        "mic_track_1based": args.mic_track,
        "speech_regions": speech_regions,
    })
    _write_json(silence_gaps_path, {
        "engine": vad_metadata.get("engine"),
        "metadata": vad_metadata,
        "media_duration_seconds": round(float(media_duration), 3),
        "mic_track_1based": args.mic_track,
        "silence_gaps": silence_gaps,
    })
    _write_json(validation_path, validation)

    _write_report(
        report_path=report_path,
        video_path=video_path,
        mic_track_1based=args.mic_track,
        media_duration_seconds=float(media_duration),
        vad_metadata=vad_metadata,
        attempts=attempts,
        speech_regions_path=speech_regions_path,
        silence_gaps_path=silence_gaps_path,
        validation_path=validation_path,
        speech_regions=speech_regions,
        silence_gaps=silence_gaps,
        validation=validation,
    )

    print("PROJECT ZENITH - SPEECH-1-FIX-2 REAL TRAINED VAD")
    print(f"engine={vad_metadata.get('engine')}")
    print("energy_fallback_used=False")
    print(f"speech_regions={speech_regions_path}")
    print(f"silence_gaps={silence_gaps_path}")
    print(f"validation={validation_path}")
    print(f"report={report_path}")
    print(f"speech_share_percent={validation.get('speech_share_percent')}")
    print(f"speech_share_status={validation.get('speech_share_status')}")
    print(f"known_failed_count={validation.get('failed_count')}")
    print(f"overall_status={validation.get('overall_status')}")

    for check in validation.get("known_speech_checks", []):
        print(
            f"SPEECH_CHECK {check.get('status')} {check.get('name')} "
            f"overlap={check.get('speech_overlap_seconds')} min={check.get('min_required_seconds')}"
        )

    for check in validation.get("known_silence_checks", []):
        print(
            f"SILENCE_CHECK {check.get('status')} {check.get('name')} "
            f"overlap={check.get('silence_overlap_seconds')} min={check.get('min_required_seconds')}"
        )

    return 0 if validation.get("overall_status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
