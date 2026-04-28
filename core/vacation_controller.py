from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.enums import Mode


VACATION_DATETIME_FORMAT = "%d.%m.%Y %H:%M"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True, frozen=True)
class VacationState:
    enabled: bool
    start_at: str | None
    end_at: str | None
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "updated_at": self.updated_at,
        }


class VacationController:
    def __init__(self, state_path: str = "data/vacation_state.json") -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.state_path.exists():
            self._write_state(
                VacationState(
                    enabled=False,
                    start_at=None,
                    end_at=None,
                    updated_at=utc_now_iso(),
                )
            )

    def get_state(self) -> VacationState:
        data = self._read_raw()

        return VacationState(
            enabled=bool(data.get("enabled", False)),
            start_at=data.get("start_at"),
            end_at=data.get("end_at"),
            updated_at=str(data.get("updated_at") or utc_now_iso()),
        )

    def set_enabled(self, enabled: bool) -> VacationState:
        current = self.get_state()
        state = VacationState(
            enabled=bool(enabled),
            start_at=current.start_at,
            end_at=current.end_at,
            updated_at=utc_now_iso(),
        )
        self._write_state(state)
        return state

    def set_window(
        self,
        start_at: str | None,
        end_at: str | None,
        *,
        enabled: bool | None = None,
    ) -> VacationState:
        normalized_start = self._normalize_datetime_string(start_at)
        normalized_end = self._normalize_datetime_string(end_at)

        if normalized_start and normalized_end:
            start_dt = datetime.strptime(normalized_start, VACATION_DATETIME_FORMAT)
            end_dt = datetime.strptime(normalized_end, VACATION_DATETIME_FORMAT)

            if end_dt <= start_dt:
                raise RuntimeError("Vacation end_at must be later than start_at")

        current = self.get_state()

        state = VacationState(
            enabled=current.enabled if enabled is None else bool(enabled),
            start_at=normalized_start,
            end_at=normalized_end,
            updated_at=utc_now_iso(),
        )
        self._write_state(state)
        return state

    def clear_window(self) -> VacationState:
        current = self.get_state()
        state = VacationState(
            enabled=current.enabled,
            start_at=None,
            end_at=None,
            updated_at=utc_now_iso(),
        )
        self._write_state(state)
        return state

    def is_active_now(self, now: datetime | None = None) -> bool:
        state = self.get_state()

        if not state.enabled:
            return False

        current_time = now or datetime.now()

        if state.start_at:
            start_dt = datetime.strptime(state.start_at, VACATION_DATETIME_FORMAT)
            if current_time < start_dt:
                return False

        if state.end_at:
            end_dt = datetime.strptime(state.end_at, VACATION_DATETIME_FORMAT)
            if current_time > end_dt:
                return False

        return True

    def get_effective_mode(self, now: datetime | None = None) -> Mode:
        return Mode.VACATION if self.is_active_now(now=now) else Mode.NORMAL

    def _normalize_datetime_string(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip()
        if not normalized:
            return None

        try:
            parsed = datetime.strptime(normalized, VACATION_DATETIME_FORMAT)
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid vacation datetime '{value}'. Expected format: {VACATION_DATETIME_FORMAT}"
            ) from exc

        return parsed.strftime(VACATION_DATETIME_FORMAT)

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.state_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise RuntimeError(f"Could not read vacation state: {exc}") from exc

    def _write_state(self, state: VacationState) -> None:
        try:
            with self.state_path.open("w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=4, ensure_ascii=False)
        except Exception as exc:
            raise RuntimeError(f"Could not write vacation state: {exc}") from exc