from pathlib import Path

from app import is_runtime_action_allowed
from core.runtime_mode_controller import RuntimeModeController
from shared.runtime_modes import RuntimeAction, RuntimeMode


def main() -> None:
    test_state_path = "data/runtime_mode_app_test.json"
    controller = RuntimeModeController(state_path=test_state_path)

    controller.set_mode(RuntimeMode.PAUSED)
    assert is_runtime_action_allowed(RuntimeAction.CONTENT_PIPELINE, controller) is False
    assert is_runtime_action_allowed(RuntimeAction.FACELESS_PIPELINE, controller) is False

    controller.set_mode(RuntimeMode.BALANCED)
    assert is_runtime_action_allowed(RuntimeAction.CONTENT_PIPELINE, controller) is False
    assert is_runtime_action_allowed(RuntimeAction.FACELESS_PIPELINE, controller) is False

    controller.set_mode(RuntimeMode.IDLE_ONLY)
    assert is_runtime_action_allowed(RuntimeAction.CONTENT_PIPELINE, controller) is True
    assert is_runtime_action_allowed(RuntimeAction.FACELESS_PIPELINE, controller) is True

    controller.set_mode(RuntimeMode.FULL_POWER)
    assert is_runtime_action_allowed(RuntimeAction.CONTENT_PIPELINE, controller) is True
    assert is_runtime_action_allowed(RuntimeAction.FACELESS_PIPELINE, controller) is True

    print("APP RUNTIME GATE SMOKE TEST PASSED")

    test_file = Path(test_state_path)
    if test_file.exists():
        test_file.unlink()


if __name__ == "__main__":
    main()