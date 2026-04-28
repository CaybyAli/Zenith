from pathlib import Path

import rerender_worker
from core.vacation_controller import VacationController
from shared.enums import Mode
from shared.runtime_modes import RuntimeAction


def main() -> None:
    test_state_path = "data/vacation_state_rerender_worker_test.json"
    original_controller = rerender_worker.vacation_controller

    try:
        rerender_worker.vacation_controller = VacationController(state_path=test_state_path)

        assert rerender_worker.get_effective_operation_mode() == Mode.NORMAL
        assert rerender_worker.is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is True
        assert rerender_worker.is_vacation_action_allowed(RuntimeAction.RERENDER_PIPELINE) is True

        rerender_worker.vacation_controller.set_enabled(True)

        assert rerender_worker.get_effective_operation_mode() == Mode.VACATION
        assert rerender_worker.is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is False
        assert rerender_worker.is_vacation_action_allowed(RuntimeAction.RERENDER_PIPELINE) is False

        rerender_worker.vacation_controller.set_enabled(False)

        assert rerender_worker.get_effective_operation_mode() == Mode.NORMAL
        assert rerender_worker.is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is True
        assert rerender_worker.is_vacation_action_allowed(RuntimeAction.RERENDER_PIPELINE) is True

        print("RERENDER WORKER VACATION GATE SMOKE TEST PASSED")

    finally:
        rerender_worker.vacation_controller = original_controller
        test_file = Path(test_state_path)
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    main()