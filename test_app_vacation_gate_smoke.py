from pathlib import Path

import app
from core.vacation_controller import VacationController
from shared.enums import Mode
from shared.runtime_modes import RuntimeAction


def main() -> None:
    test_state_path = "data/vacation_state_app_test.json"
    original_controller = app.vacation_controller

    try:
        app.vacation_controller = VacationController(state_path=test_state_path)

        assert app.get_effective_operation_mode() == Mode.NORMAL
        assert app.is_vacation_action_allowed(RuntimeAction.CONTENT_PIPELINE) is True
        assert app.is_vacation_action_allowed(RuntimeAction.FACELESS_PIPELINE) is True
        assert app.is_vacation_action_allowed(RuntimeAction.RERENDER_PIPELINE) is True

        app.vacation_controller.set_enabled(True)

        assert app.get_effective_operation_mode() == Mode.VACATION
        assert app.is_vacation_action_allowed(RuntimeAction.CONTENT_PIPELINE) is False
        assert app.is_vacation_action_allowed(RuntimeAction.FACELESS_PIPELINE) is False
        assert app.is_vacation_action_allowed(RuntimeAction.RERENDER_PIPELINE) is False
        assert app.is_vacation_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is True
        assert app.is_vacation_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH) is True

        app.vacation_controller.set_enabled(False)

        assert app.get_effective_operation_mode() == Mode.NORMAL
        assert app.is_vacation_action_allowed(RuntimeAction.CONTENT_PIPELINE) is True

        print("APP VACATION GATE SMOKE TEST PASSED")

    finally:
        app.vacation_controller = original_controller
        test_file = Path(test_state_path)
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    main()