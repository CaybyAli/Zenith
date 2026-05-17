from pathlib import Path

import dashboard
from core.runtime_mode_controller import RuntimeModeController
from shared.runtime_modes import RuntimeAction, RuntimeMode


def main() -> None:
    test_state_path = "data/runtime_mode_dashboard_test.json"
    original_controller = dashboard.runtime_mode_controller

    try:
        dashboard.runtime_mode_controller = RuntimeModeController(state_path=test_state_path)

        dashboard.runtime_mode_controller.set_mode(RuntimeMode.PAUSED)
        assert dashboard.is_runtime_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is False
        assert dashboard.is_runtime_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH) is False
        assert dashboard.is_runtime_action_allowed(RuntimeAction.REPOST_DISPATCH) is False
        assert dashboard.is_runtime_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is False

        dashboard.runtime_mode_controller.set_mode(RuntimeMode.BALANCED)
        assert dashboard.is_runtime_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is True
        assert dashboard.is_runtime_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH) is True
        assert dashboard.is_runtime_action_allowed(RuntimeAction.REPOST_DISPATCH) is True
        assert dashboard.is_runtime_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is False

        dashboard.runtime_mode_controller.set_mode(RuntimeMode.IDLE_ONLY)
        assert dashboard.is_runtime_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is False
        assert dashboard.is_runtime_action_allowed(RuntimeAction.SHORT_RETRY_DISPATCH) is False
        assert dashboard.is_runtime_action_allowed(RuntimeAction.REPOST_DISPATCH) is False
        assert dashboard.is_runtime_action_allowed(RuntimeAction.RERENDER_QUEUE_INTAKE) is True

        print("DASHBOARD RUNTIME GATE SMOKE TEST PASSED")

    finally:
        dashboard.runtime_mode_controller = original_controller
        test_file = Path(test_state_path)
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    main()