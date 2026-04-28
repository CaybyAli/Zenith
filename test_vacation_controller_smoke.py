from datetime import datetime
from pathlib import Path

from core.vacation_controller import VacationController
from shared.enums import Mode


def main() -> None:
    test_state_path = "data/vacation_state_test.json"
    controller = VacationController(state_path=test_state_path)

    state = controller.get_state()
    assert state.enabled is False
    assert controller.is_active_now() is False
    assert controller.get_effective_mode() == Mode.NORMAL

    controller.set_enabled(True)
    assert controller.is_active_now() is True
    assert controller.get_effective_mode() == Mode.VACATION

    controller.set_window("20.04.2026 10:00", "25.04.2026 18:00", enabled=True)
    assert controller.is_active_now(datetime(2026, 4, 19, 12, 0)) is False
    assert controller.is_active_now(datetime(2026, 4, 22, 12, 0)) is True
    assert controller.is_active_now(datetime(2026, 4, 26, 12, 0)) is False
    assert controller.get_effective_mode(datetime(2026, 4, 22, 12, 0)) == Mode.VACATION
    assert controller.get_effective_mode(datetime(2026, 4, 26, 12, 0)) == Mode.NORMAL

    controller.clear_window()
    state = controller.get_state()
    assert state.start_at is None
    assert state.end_at is None

    controller.set_enabled(False)
    assert controller.is_active_now() is False
    assert controller.get_effective_mode() == Mode.NORMAL

    print("VACATION CONTROLLER SMOKE TEST PASSED")
    print(controller.get_state().to_dict())

    test_file = Path(test_state_path)
    if test_file.exists():
        test_file.unlink()


if __name__ == "__main__":
    main()