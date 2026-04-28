from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shared.runtime_modes import RuntimeAction, RuntimeMode


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True, frozen=True)
class RuntimeModeState:
    mode: RuntimeMode
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "updated_at": self.updated_at,
        }


class RuntimeModeController:
    _ALLOWED_ACTIONS: dict[RuntimeMode, set[RuntimeAction]] = {
        RuntimeMode.FULL_POWER: {
            RuntimeAction.DASHBOARD_REVIEW,
            RuntimeAction.MODE_SWITCH,
            RuntimeAction.PUBLISH_DISPATCH,
            RuntimeAction.REPOST_DISPATCH,
            RuntimeAction.SHORT_RETRY_DISPATCH,
            RuntimeAction.RERENDER_QUEUE_INTAKE,
            RuntimeAction.RERENDER_PIPELINE,
            RuntimeAction.CONTENT_PIPELINE,
            RuntimeAction.FACELESS_PIPELINE,
        },
        RuntimeMode.BALANCED: {
            RuntimeAction.DASHBOARD_REVIEW,
            RuntimeAction.MODE_SWITCH,
            RuntimeAction.PUBLISH_DISPATCH,
            RuntimeAction.REPOST_DISPATCH,
            RuntimeAction.SHORT_RETRY_DISPATCH,
        },
        RuntimeMode.STREAM_SAFE: {
            RuntimeAction.DASHBOARD_REVIEW,
            RuntimeAction.MODE_SWITCH,
        },
        RuntimeMode.GAMING_SAFE: {
            RuntimeAction.DASHBOARD_REVIEW,
            RuntimeAction.MODE_SWITCH,
        },
        RuntimeMode.IDLE_ONLY: {
            RuntimeAction.DASHBOARD_REVIEW,
            RuntimeAction.MODE_SWITCH,
            RuntimeAction.RERENDER_QUEUE_INTAKE,
            RuntimeAction.RERENDER_PIPELINE,
            RuntimeAction.CONTENT_PIPELINE,
            RuntimeAction.FACELESS_PIPELINE,
        },
        RuntimeMode.PAUSED: {
            RuntimeAction.DASHBOARD_REVIEW,
            RuntimeAction.MODE_SWITCH,
        },
    }

    def __init__(self, state_path: str = "data/runtime_mode.json") -> None:
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.state_path.exists():
            self._write_state(
                RuntimeModeState(
                    mode=RuntimeMode.FULL_POWER,
                    updated_at=utc_now_iso(),
                )
            )

    def get_state(self) -> RuntimeModeState:
        data = self._read_raw()

        try:
            mode = RuntimeMode(str(data.get("mode", RuntimeMode.FULL_POWER.value)).strip().lower())
        except ValueError as exc:
            raise RuntimeError(f"Invalid runtime mode in {self.state_path}: {data.get('mode')}") from exc

        updated_at = str(data.get("updated_at") or utc_now_iso())

        return RuntimeModeState(
            mode=mode,
            updated_at=updated_at,
        )

    def get_mode(self) -> RuntimeMode:
        return self.get_state().mode

    def set_mode(self, mode: RuntimeMode | str) -> RuntimeModeState:
        if isinstance(mode, RuntimeMode):
            normalized_mode = mode
        else:
            try:
                normalized_mode = RuntimeMode(str(mode).strip().lower())
            except ValueError as exc:
                raise RuntimeError(f"Invalid runtime mode: {mode}") from exc

        state = RuntimeModeState(
            mode=normalized_mode,
            updated_at=utc_now_iso(),
        )
        self._write_state(state)
        return state

    def get_allowed_actions(self, mode: RuntimeMode | str | None = None) -> set[RuntimeAction]:
        normalized_mode = self.get_mode() if mode is None else self._normalize_mode(mode)
        return set(self._ALLOWED_ACTIONS[normalized_mode])

    def is_action_allowed(self, action: RuntimeAction | str) -> bool:
        normalized_action = self._normalize_action(action)
        return normalized_action in self._ALLOWED_ACTIONS[self.get_mode()]

    def _normalize_mode(self, mode: RuntimeMode | str) -> RuntimeMode:
        if isinstance(mode, RuntimeMode):
            return mode

        try:
            return RuntimeMode(str(mode).strip().lower())
        except ValueError as exc:
            raise RuntimeError(f"Invalid runtime mode: {mode}") from exc

    def _normalize_action(self, action: RuntimeAction | str) -> RuntimeAction:
        if isinstance(action, RuntimeAction):
            return action

        try:
            return RuntimeAction(str(action).strip().lower())
        except ValueError as exc:
            raise RuntimeError(f"Invalid runtime action: {action}") from exc

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.state_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise RuntimeError(f"Could not read runtime mode state: {exc}") from exc

    def _write_state(self, state: RuntimeModeState) -> None:
        try:
            with self.state_path.open("w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=4, ensure_ascii=False)
        except Exception as exc:
            raise RuntimeError(f"Could not write runtime mode state: {exc}") from exc