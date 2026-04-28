from __future__ import annotations

from dataclasses import dataclass

from shared.enums import AutopublishClass, Mode
from shared.errors import ModeError


@dataclass(slots=True)
class ModePolicy:
    mode: Mode
    allowed_autopublish_classes: set[AutopublishClass]
    approval_required_for_manual_only: bool
    time_window_required: bool


class ModeController:
    def __init__(self, initial_mode: Mode = Mode.NORMAL) -> None:
        self._mode = initial_mode

    def set_mode(self, mode: Mode) -> None:
        if not isinstance(mode, Mode):
            raise ModeError(f"Invalid mode: {mode}")
        self._mode = mode

    def get_mode(self) -> Mode:
        return self._mode

    def get_policy(self) -> ModePolicy:
        if self._mode == Mode.NORMAL:
            return ModePolicy(
                mode=Mode.NORMAL,
                allowed_autopublish_classes={
                    AutopublishClass.MANUAL_ONLY,
                    AutopublishClass.CONDITIONAL,
                    AutopublishClass.SAFE_AUTO,
                },
                approval_required_for_manual_only=True,
                time_window_required=False,
            )

        if self._mode == Mode.VACATION:
            return ModePolicy(
                mode=Mode.VACATION,
                allowed_autopublish_classes={
                    AutopublishClass.CONDITIONAL,
                    AutopublishClass.SAFE_AUTO,
                },
                approval_required_for_manual_only=True,
                time_window_required=True,
            )

        raise ModeError(f"No policy defined for mode: {self._mode}")