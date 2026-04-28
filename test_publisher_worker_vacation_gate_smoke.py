from pathlib import Path

import publisher_worker
from core.vacation_controller import VacationController
from shared.enums import Mode
from shared.runtime_modes import RuntimeAction


def main() -> None:
    test_state_path = "data/vacation_state_publisher_worker_test.json"
    original_controller = publisher_worker.vacation_controller

    try:
        publisher_worker.vacation_controller = VacationController(state_path=test_state_path)

        assert publisher_worker.get_effective_operation_mode() == Mode.NORMAL
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is True
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH) is True
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.REPOST_DISPATCH) is True
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is True

        publisher_worker.vacation_controller.set_enabled(True)

        assert publisher_worker.get_effective_operation_mode() == Mode.VACATION
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is True
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH) is True
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.REPOST_DISPATCH) is False
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is False

        publisher_worker.vacation_controller.set_enabled(False)

        assert publisher_worker.get_effective_operation_mode() == Mode.NORMAL
        assert publisher_worker.is_vacation_action_allowed(RuntimeAction.REPOST_DISPATCH) is True

        print("PUBLISHER WORKER VACATION GATE SMOKE TEST PASSED")

    finally:
        publisher_worker.vacation_controller = original_controller
        test_file = Path(test_state_path)
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    main()