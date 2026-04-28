from pathlib import Path

from core.runtime_mode_controller import RuntimeModeController
from shared.runtime_modes import RuntimeAction, RuntimeMode


def main() -> None:
    test_state_path = "data/runtime_mode_test.json"
    controller = RuntimeModeController(state_path=test_state_path)

    state = controller.set_mode(RuntimeMode.PAUSED)
    assert state.mode == RuntimeMode.PAUSED
    assert controller.is_action_allowed(RuntimeAction.MODE_SWITCH) is True
    assert controller.is_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is False
    assert controller.is_action_allowed(RuntimeAction.RERENDER_PIPELINE) is False

    state = controller.set_mode(RuntimeMode.IDLE_ONLY)
    assert state.mode == RuntimeMode.IDLE_ONLY
    assert controller.is_action_allowed(RuntimeAction.RERENDER_PIPELINE) is True
    assert controller.is_action_allowed(RuntimeAction.CONTENT_PIPELINE) is True
    assert controller.is_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is False

    state = controller.set_mode(RuntimeMode.FULL_POWER)
    assert state.mode == RuntimeMode.FULL_POWER
    assert controller.is_action_allowed(RuntimeAction.PUBLISH_DISPATCH) is True
    assert controller.is_action_allowed(RuntimeAction.RERENDER_PIPELINE) is True

    print("RUNTIME MODE CONTROLLER SMOKE TEST PASSED")
    print(controller.get_state().to_dict())

    test_file = Path(test_state_path)
    if test_file.exists():
        test_file.unlink()


if __name__ == "__main__":
    main()