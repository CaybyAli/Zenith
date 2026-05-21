from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


DEFAULT_TARGET_I = -14.0
DEFAULT_TARGET_TP = -1.0
DEFAULT_LRA = 11


@dataclass
class AudioNormalizationResult:
    input_i: float
    input_lra: float
    input_tp: float
    input_thresh: float
    target_i: float
    target_tp: float
    filter_string: str
    skipped: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "input_i": float(self.input_i),
            "input_lra": float(self.input_lra),
            "input_tp": float(self.input_tp),
            "input_thresh": float(self.input_thresh),
            "target_i": float(self.target_i),
            "target_tp": float(self.target_tp),
            "filter_string": str(self.filter_string),
            "skipped": bool(self.skipped),
            "warnings": list(self.warnings),
        }


class AudioNormalizer:
    def __init__(
        self,
        target_i: float = DEFAULT_TARGET_I,
        target_tp: float = DEFAULT_TARGET_TP,
    ) -> None:
        self.target_i = self._safe_float(target_i, DEFAULT_TARGET_I)
        self.target_tp = self._safe_float(target_tp, DEFAULT_TARGET_TP)

    @classmethod
    def from_contract(cls, contract) -> "AudioNormalizer":
        """Liest target_lufs und target_tp aus output_format_contract sicher aus.
        Fallback: target_i=-14.0, target_tp=-1.0
        """
        target_i = cls._contract_value(
            contract,
            ("target_lufs", "target_i", "audio_target_lufs"),
            DEFAULT_TARGET_I,
        )
        target_tp = cls._contract_value(
            contract,
            ("target_tp", "audio_target_tp", "true_peak"),
            DEFAULT_TARGET_TP,
        )
        return cls(target_i=target_i, target_tp=target_tp)

    def build_pass1_command(self, input_path: str) -> list[str]:
        """
        Gibt FFmpeg-Pass-1-Kommando als Liste zurück (subprocess-ready).
        Format: ffmpeg -i {input} -af loudnorm=I={target_i}:TP={target_tp}:LRA=11:print_format=json -f null -
        """
        return [
            "ffmpeg",
            "-i",
            str(input_path),
            "-af",
            (
                f"loudnorm=I={self.target_i}:TP={self.target_tp}:"
                f"LRA={DEFAULT_LRA}:print_format=json"
            ),
            "-f",
            "null",
            "-",
        ]

    def parse_pass1_output(self, ffmpeg_stderr: str) -> dict:
        """
        Parst JSON-Block aus ffmpeg stderr/stdout.
        Sucht { ... } Block der loudnorm-Ausgabe.
        Gibt dict mit input_i, input_lra, input_tp, input_thresh zurück.
        Wenn kein JSON gefunden: leeres dict, kein Crash.
        """
        try:
            text = str(ffmpeg_stderr or "")
        except Exception:
            return {}

        try:
            for match in re.finditer(r"\{[\s\S]*?\}", text):
                try:
                    payload = json.loads(match.group(0))
                except Exception:
                    continue

                if not isinstance(payload, dict):
                    continue

                if not {
                    "input_i",
                    "input_lra",
                    "input_tp",
                    "input_thresh",
                }.issubset(set(payload.keys())):
                    continue

                return {
                    "input_i": self._safe_float(payload.get("input_i"), 0.0),
                    "input_lra": self._safe_float(payload.get("input_lra"), 0.0),
                    "input_tp": self._safe_float(payload.get("input_tp"), 0.0),
                    "input_thresh": self._safe_float(
                        payload.get("input_thresh"),
                        0.0,
                    ),
                }
        except Exception:
            return {}

        return {}

    def build_pass2_filter(self, measured: dict) -> str:
        """
        Baut deterministischen loudnorm-Pass-2-Filter-String.
        Wenn measured leer: leerer String. skipped=True wird in build_result gesetzt.
        """
        if not isinstance(measured, dict) or not measured:
            return ""

        input_i = self._safe_float(measured.get("input_i"), 0.0)
        input_lra = self._safe_float(measured.get("input_lra"), 0.0)
        input_tp = self._safe_float(measured.get("input_tp"), 0.0)
        input_thresh = self._safe_float(measured.get("input_thresh"), 0.0)

        return (
            f"loudnorm=I={self.target_i}:TP={self.target_tp}:LRA={DEFAULT_LRA}:"
            f"measured_I={input_i:.2f}:"
            f"measured_LRA={input_lra:.2f}:"
            f"measured_TP={input_tp:.2f}:"
            f"measured_thresh={input_thresh:.2f}:"
            "offset=0.0:linear=true:print_format=none"
        )

    def build_result(self, measured: dict) -> AudioNormalizationResult:
        """Kombiniert alles zu AudioNormalizationResult."""
        if not isinstance(measured, dict) or not measured:
            return AudioNormalizationResult(
                input_i=0.0,
                input_lra=0.0,
                input_tp=0.0,
                input_thresh=0.0,
                target_i=self.target_i,
                target_tp=self.target_tp,
                filter_string="",
                skipped=True,
                warnings=["audio_normalization_skipped_no_measured_loudnorm_data"],
            )

        return AudioNormalizationResult(
            input_i=self._safe_float(measured.get("input_i"), 0.0),
            input_lra=self._safe_float(measured.get("input_lra"), 0.0),
            input_tp=self._safe_float(measured.get("input_tp"), 0.0),
            input_thresh=self._safe_float(measured.get("input_thresh"), 0.0),
            target_i=self.target_i,
            target_tp=self.target_tp,
            filter_string=self.build_pass2_filter(measured),
            skipped=False,
            warnings=[],
        )

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @classmethod
    def _contract_value(
        cls,
        contract: Any,
        names: tuple[str, ...],
        default: float,
    ) -> float:
        for name in names:
            try:
                value = getattr(contract, name, None)
            except Exception:
                value = None

            if value is None and isinstance(contract, dict):
                try:
                    value = contract.get(name)
                except Exception:
                    value = None

            if value is not None:
                return cls._safe_float(value, default)

        return float(default)
