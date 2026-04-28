import rerender_worker


def main() -> None:
    assert callable(rerender_worker.get_effective_operation_mode)
    assert callable(rerender_worker.is_vacation_action_allowed)
    assert callable(rerender_worker.create_rerender_job_from_queue)

    print("RERENDER WORKER DEDUP SMOKE TEST PASSED")


if __name__ == "__main__":
    main()