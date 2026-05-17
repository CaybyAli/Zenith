from pathlib import Path

import dashboard
from core.vacation_controller import VacationController
from shared.runtime_modes import RuntimeAction


def main() -> None:
    test_state_path = "data/vacation_state_dashboard_gate_test.json"
    original_controller = dashboard.vacation_controller

    try:
        dashboard.vacation_controller = VacationController(state_path=test_state_path)

        assert dashboard.is_vacation_action_allowed(RuntimeAction.REPOST_DISPATCH) is True
        assert dashboard.is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is True
        assert dashboard.is_vacation_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is True
        assert dashboard.is_vacation_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH) is True

        dashboard.vacation_controller.set_enabled(True)

        assert dashboard.is_vacation_action_allowed(RuntimeAction.REPOST_DISPATCH) is False
        assert dashboard.is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is False
        assert dashboard.is_vacation_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is True
        assert dashboard.is_vacation_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH) is True

        dashboard.vacation_controller.set_enabled(False)

        assert dashboard.is_vacation_action_allowed(RuntimeAction.REPOST_DISPATCH) is True
        assert dashboard.is_vacation_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is True

        print("DASHBOARD VACATION GATE SMOKE TEST PASSED")

    finally:
        dashboard.vacation_controller = original_controller
        test_file = Path(test_state_path)
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    main()