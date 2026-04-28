from __future__ import annotations

import os
import shutil

from core.jarvis_command_service import JarvisCommandService
from core.jarvis_status_service import JarvisStatusService
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from shared.jarvis_enums import JarvisCommandType


def main() -> None:
    test_dir = "tmp/jarvis_blocked_warning_publish_test"
    exports_dir = os.path.join(test_dir, "exports")
    runtime_state_path = os.path.join(test_dir, "runtime_mode.json")
    vacation_state_path = os.path.join(test_dir, "vacation_state.json")

    shutil.rmtree(test_dir, ignore_errors=True)
    os.makedirs(exports_dir, exist_ok=True)

    status_service = JarvisStatusService(
        runtime_mode_controller=RuntimeModeController(state_path=runtime_state_path),
        vacation_controller=VacationController(state_path=vacation_state_path),
    )
    command_service = JarvisCommandService(status_service=status_service)

    blocked_response = command_service.handle_command(
        "Welche Jobs sind blockiert?",
        base_path=exports_dir,
    )
    warning_response = command_service.handle_command(
        "Zeig mir Warnfälle.",
        base_path=exports_dir,
    )
    publish_response = command_service.handle_command(
        "Wie ist der Publish Status?",
        base_path=exports_dir,
    )

    assert blocked_response.command_type == JarvisCommandType.BLOCKED_JOBS
    assert warning_response.command_type == JarvisCommandType.WARNING_CASES
    assert publish_response.command_type == JarvisCommandType.PUBLISH_STATUS

    assert "0 Jobs" in blocked_response.summary
    assert "Warnfälle" in warning_response.title
    assert "Published=" in publish_response.summary

    print("JARVIS BLOCKED/WARNING/PUBLISH SMOKE TEST PASSED")
    print(
        {
            "blocked_summary": blocked_response.summary,
            "warning_summary": warning_response.summary,
            "publish_summary": publish_response.summary,
        }
    )


if __name__ == "__main__":
    main()