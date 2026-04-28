from __future__ import annotations

import os
import shutil

from core.jarvis_status_service import JarvisStatusService
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController


def main() -> None:
    test_dir = "tmp/jarvis_status_service_test"
    exports_dir = os.path.join(test_dir, "exports")
    runtime_state_path = os.path.join(test_dir, "runtime_mode.json")
    vacation_state_path = os.path.join(test_dir, "vacation_state.json")

    shutil.rmtree(test_dir, ignore_errors=True)
    os.makedirs(exports_dir, exist_ok=True)

    runtime_controller = RuntimeModeController(state_path=runtime_state_path)
    vacation_controller = VacationController(state_path=vacation_state_path)

    service = JarvisStatusService(
        runtime_mode_controller=runtime_controller,
        vacation_controller=vacation_controller,
    )

    runtime_status = service.get_runtime_status()
    vacation_status = service.get_vacation_status()
    review_status = service.get_review_status(base_path=exports_dir)
    kpi_summary = service.get_kpi_summary(base_path=exports_dir)
    feedback_summary = service.get_feedback_summary(base_path=exports_dir)
    system_status = service.get_system_status(base_path=exports_dir)

    assert runtime_status["mode"] == "full_power"
    assert vacation_status["enabled"] is False
    assert review_status["total_jobs"] == 0
    assert kpi_summary["total_entries"] == 0
    assert feedback_summary["total_records"] == 0
    assert isinstance(system_status["warnings"], list)

    print("JARVIS STATUS SERVICE SMOKE TEST PASSED")
    print(
        {
            "runtime_mode": runtime_status["mode"],
            "vacation_enabled": vacation_status["enabled"],
            "total_jobs": review_status["total_jobs"],
            "kpi_entries": kpi_summary["total_entries"],
            "feedback_records": feedback_summary["total_records"],
            "warnings": len(system_status["warnings"]),
        }
    )


if __name__ == "__main__":
    main()