from __future__ import annotations

import json
import os
import shutil

from core.jarvis_command_service import JarvisCommandService
from core.jarvis_status_service import JarvisStatusService
from core.queue_store import QueueStore
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from models.queue_entry import QueueEntry
from shared.jarvis_enums import JarvisCommandType
from shared.opportunity_enums import OpportunityLevel
from shared.opportunity_review_enums import OpportunityReviewStatus
from shared.queue_enums import QueueState
from shared.trend_qualification_enums import LifespanClass


def main() -> None:
    test_dir = "tmp/jarvis_queue_maintenance_test"
    exports_dir = os.path.join(test_dir, "exports")
    data_dir = os.path.join(test_dir, "data")
    runtime_state_path = os.path.join(data_dir, "runtime_mode.json")
    vacation_state_path = os.path.join(data_dir, "vacation_state.json")
    queue_entries_path = os.path.join(data_dir, "queue_entries.json")
    rerender_queue_file = os.path.join(data_dir, "rerender_queue.json")
    rerender_jobs_file = os.path.join(data_dir, "rerender_jobs.json")

    shutil.rmtree(test_dir, ignore_errors=True)
    os.makedirs(exports_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    with open(rerender_queue_file, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)

    with open(rerender_jobs_file, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)

    queue_store = QueueStore(queue_entries_path=queue_entries_path)
    queue_store.create_queue_entry(
        QueueEntry(
            queue_entry_id="queue_test_001",
            dedupe_key="dedupe_test_001",
            source_review_view_id="review_001",
            source_opportunity_id="opp_001",
            source_signal_id="signal_001",
            topic_label="Test Topic Strong",
            platform="youtube",
            channel_type="gaming_main",
            channel_group="gaming",
            content_kind="longform",
            queue_state=QueueState.QUEUED,
            opportunity_score=88.5,
            opportunity_level=OpportunityLevel.HIGH,
            lifespan_class=LifespanClass.SHORT,
            review_status=OpportunityReviewStatus.APPROVED,
            review_summary="Strong queue candidate",
            block_reason=None,
        )
    )
    queue_store.create_queue_entry(
        QueueEntry(
            queue_entry_id="queue_test_002",
            dedupe_key="dedupe_test_002",
            source_review_view_id="review_002",
            source_opportunity_id="opp_002",
            source_signal_id="signal_002",
            topic_label="Test Topic Blocked",
            platform="tiktok",
            channel_type="faceless_trend",
            channel_group="faceless",
            content_kind="short",
            queue_state=QueueState.BLOCKED,
            opportunity_score=41.0,
            opportunity_level=OpportunityLevel.LOW,
            lifespan_class=LifespanClass.SHORT,
            review_status=OpportunityReviewStatus.PENDING,
            review_summary="Blocked queue candidate",
            block_reason="manual_hold",
        )
    )

    status_service = JarvisStatusService(
        runtime_mode_controller=RuntimeModeController(state_path=runtime_state_path),
        vacation_controller=VacationController(state_path=vacation_state_path),
        queue_store=queue_store,
    )
    command_service = JarvisCommandService(status_service=status_service)

    queue_response = command_service.handle_command(
        "Wie ist der Queue Status?",
        base_path=exports_dir,
        rerender_queue_file=rerender_queue_file,
        rerender_jobs_file=rerender_jobs_file,
    )
    maintenance_response = command_service.handle_command(
        "Wie ist der Maintenance Status?",
        base_path=exports_dir,
        rerender_queue_file=rerender_queue_file,
        rerender_jobs_file=rerender_jobs_file,
    )

    assert queue_response.command_type == JarvisCommandType.QUEUE_STATUS
    assert maintenance_response.command_type == JarvisCommandType.MAINTENANCE_STATUS

    assert "2 Queue-Einträge" in queue_response.summary
    assert queue_response.title == "Queue Status"
    assert maintenance_response.title == "Maintenance Status"
    assert "Integrity-Issues=" in maintenance_response.summary

    print("JARVIS QUEUE/MAINTENANCE SMOKE TEST PASSED")
    print(
        {
            "queue_summary": queue_response.summary,
            "maintenance_summary": maintenance_response.summary,
        }
    )


if __name__ == "__main__":
    main()