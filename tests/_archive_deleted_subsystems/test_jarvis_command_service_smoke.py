from __future__ import annotations

import os
import shutil

from core.jarvis_command_service import JarvisCommandService
from core.jarvis_status_service import JarvisStatusService
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from shared.jarvis_enums import JarvisCommandType


def main() -> None:
    test_dir = "tmp/jarvis_command_service_test"
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

    response = command_service.handle_command(
        "Wie ist der Systemstatus?",
        base_path=exports_dir,
    )

    assert response.command_type == JarvisCommandType.SYSTEM_STATUS
    assert "Runtime =" in response.summary
    assert isinstance(response.evidence_sections, list)

    print("JARVIS COMMAND SERVICE SMOKE TEST PASSED")
    print(response.to_dict())


if __name__ == "__main__":
    main()