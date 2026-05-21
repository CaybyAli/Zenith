from __future__ import annotations

import ctypes
import logging
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


DEFAULT_MODEL_PRIORITY = [
    {"model_id": "qwen2.5-32b-awq", "min_vram_gb": 18.0, "min_ram_gb": 16.0},
    {"model_id": "llama-3.3-70b-q4", "min_vram_gb": 40.0, "min_ram_gb": 32.0},
    {"model_id": "qwen2.5-14b-q4", "min_vram_gb": 10.0, "min_ram_gb": 12.0},
    {"model_id": "qwen2.5-7b-q4", "min_vram_gb": 5.0, "min_ram_gb": 8.0},
    {"model_id": "qwen2.5-3b-q4", "min_vram_gb": 0.0, "min_ram_gb": 4.0},
]


@dataclass(frozen=True)
class ModelCapabilityResolver:
    """
    Runtime-Resolver für lokale LLM-Modelle.

    Erkennt GPU/VRAM/RAM zur Laufzeit und wählt das erste Modell aus
    DEFAULT_MODEL_PRIORITY, dessen Mindestanforderungen erfüllt sind.
    Kein Crash bei fehlendem nvidia-smi, fehlendem torch oder CPU-only Systemen.
    """

    gpu_available: bool
    gpu_name: str | None
    vram_gb: float
    ram_gb: float
    model_priority: list[dict[str, Any]] = field(default_factory=lambda: list(DEFAULT_MODEL_PRIORITY))
    _selected_model: str = ""
    _reason: str = ""
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def detect(cls) -> "ModelCapabilityResolver":
        """Erkennt Hardware und wählt bestes Modell. Kein Crash bei fehlender GPU."""
        warnings: list[str] = []

        gpu_name, vram_gb, gpu_warnings = cls._detect_gpu()
        warnings.extend(gpu_warnings)

        ram_gb, ram_warnings = cls._detect_ram_gb()
        warnings.extend(ram_warnings)

        gpu_available = bool(gpu_name and vram_gb > 0.0)

        selected_model, reason = cls._select_model(
            vram_gb=vram_gb,
            ram_gb=ram_gb,
            priority=DEFAULT_MODEL_PRIORITY,
        )

        resolver = cls(
            gpu_available=gpu_available,
            gpu_name=gpu_name,
            vram_gb=vram_gb,
            ram_gb=ram_gb,
            model_priority=list(DEFAULT_MODEL_PRIORITY),
            _selected_model=selected_model,
            _reason=reason,
            warnings=warnings,
        )

        logger.info(
            "[MODEL-CAPABILITY-RESOLVER] selected_model=%s gpu_available=%s "
            "gpu_name=%s vram_gb=%.2f ram_gb=%.2f reason=%s warnings=%s",
            resolver.selected_model,
            resolver.gpu_available,
            resolver.gpu_name or "none",
            resolver.vram_gb,
            resolver.ram_gb,
            resolver.reason,
            resolver.warnings,
        )

        return resolver

    @property
    def selected_model(self) -> str:
        """ID des gewählten Modells."""
        return self._selected_model

    @property
    def reason(self) -> str:
        """Kurze Begründung der Wahl (wird geloggt)."""
        return self._reason

    def to_dict(self) -> dict[str, Any]:
        """Für Logging/Report."""
        return {
            "selected_model": self.selected_model,
            "reason": self.reason,
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "vram_gb": self.vram_gb,
            "ram_gb": self.ram_gb,
            "warnings": list(self.warnings),
            "model_priority": [dict(item) for item in self.model_priority],
        }

    @classmethod
    def _select_model(
        cls,
        vram_gb: float,
        ram_gb: float,
        priority: list[dict[str, Any]],
    ) -> tuple[str, str]:
        for entry in priority:
            model_id = str(entry["model_id"])
            min_vram_gb = float(entry["min_vram_gb"])
            min_ram_gb = float(entry["min_ram_gb"])

            if vram_gb >= min_vram_gb and ram_gb >= min_ram_gb:
                return (
                    model_id,
                    (
                        f"selected {model_id}: detected vram={vram_gb:.2f}GB "
                        f"ram={ram_gb:.2f}GB meets minimum "
                        f"vram={min_vram_gb:.2f}GB ram={min_ram_gb:.2f}GB"
                    ),
                )

        fallback = str(priority[-1]["model_id"]) if priority else "qwen2.5-3b-q4"
        return (
            fallback,
            (
                f"selected safety fallback {fallback}: no configured model fully matched "
                f"detected vram={vram_gb:.2f}GB ram={ram_gb:.2f}GB"
            ),
        )

    @classmethod
    def _detect_gpu(cls) -> tuple[str | None, float, list[str]]:
        warnings: list[str] = []

        gpu_name, vram_gb = cls._detect_gpu_with_nvidia_smi()
        if gpu_name and vram_gb > 0.0:
            return gpu_name, vram_gb, warnings

        warnings.append("nvidia_smi_unavailable_or_no_gpu")

        torch_gpu_name, torch_vram_gb, torch_warning = cls._detect_gpu_with_torch()
        if torch_warning:
            warnings.append(torch_warning)

        if torch_gpu_name and torch_vram_gb > 0.0:
            return torch_gpu_name, torch_vram_gb, warnings

        return None, 0.0, warnings

    @classmethod
    def _detect_gpu_with_nvidia_smi(cls) -> tuple[str | None, float]:
        try:
            completed = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                shell=False,
                timeout=5,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return None, 0.0

        if completed.returncode != 0:
            return None, 0.0

        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            return None, 0.0

        first_line = lines[0]
        parts = [part.strip() for part in first_line.split(",")]
        if len(parts) < 2:
            return None, 0.0

        gpu_name = parts[0] or None

        try:
            vram_mb = float(parts[1])
        except ValueError:
            return gpu_name, 0.0

        return gpu_name, round(vram_mb / 1024.0, 2)

    @classmethod
    def _detect_gpu_with_torch(cls) -> tuple[str | None, float, str | None]:
        try:
            import torch  # type: ignore
        except Exception:
            return None, 0.0, "torch_unavailable_cpu_only"

        try:
            if not torch.cuda.is_available():
                return None, 0.0, "torch_cuda_unavailable_cpu_only"

            device_index = 0
            gpu_name = str(torch.cuda.get_device_name(device_index))
            props = torch.cuda.get_device_properties(device_index)
            total_memory = float(getattr(props, "total_memory", 0.0) or 0.0)

            if total_memory <= 0.0:
                return gpu_name, 0.0, "torch_cuda_memory_unknown"

            return gpu_name, round(total_memory / (1024.0**3), 2), None
        except Exception:
            return None, 0.0, "torch_cuda_detection_failed"

    @classmethod
    def _detect_ram_gb(cls) -> tuple[float, list[str]]:
        warnings: list[str] = []

        psutil_ram = cls._detect_ram_with_psutil()
        if psutil_ram > 0.0:
            return psutil_ram, warnings

        warnings.append("psutil_unavailable")

        os_ram = cls._detect_ram_with_os()
        if os_ram > 0.0:
            return os_ram, warnings

        windows_ram = cls._detect_ram_with_windows_ctypes()
        if windows_ram > 0.0:
            return windows_ram, warnings

        warnings.append("ram_detection_failed")
        return 0.0, warnings

    @classmethod
    def _detect_ram_with_psutil(cls) -> float:
        try:
            import psutil  # type: ignore
        except Exception:
            return 0.0

        try:
            total = float(psutil.virtual_memory().total)
        except Exception:
            return 0.0

        return round(total / (1024.0**3), 2)

    @classmethod
    def _detect_ram_with_os(cls) -> float:
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            physical_pages = os.sysconf("SC_PHYS_PAGES")
            total = float(page_size * physical_pages)
        except Exception:
            return 0.0

        return round(total / (1024.0**3), 2)

    @classmethod
    def _detect_ram_with_windows_ctypes(cls) -> float:
        if os.name != "nt":
            return 0.0

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        try:
            memory_status = MEMORYSTATUSEX()
            memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
            if not ok:
                return 0.0
            return round(float(memory_status.ullTotalPhys) / (1024.0**3), 2)
        except Exception:
            return 0.0
