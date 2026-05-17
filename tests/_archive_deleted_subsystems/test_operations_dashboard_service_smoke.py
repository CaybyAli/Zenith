from __future__ import annotations

import json
import os
import shutil

from core.operations_dashboard_service import OperationsDashboardService
from core.queue_store import QueueStore
from models.queue_entry import QueueEntry
from shared.opportunity_enums import OpportunityLevel
from shared.opportunity_review_enums import OpportunityReviewStatus
from shared.queue_enums import QueueState
from shared.trend_qualification_enums import LifespanClass
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    test_dir = "tmp/operations_dashboard_service_test"
    exports_dir = os.path.join(test_dir, "exports")
    data_dir = os.path.join(test_dir, "data")

    shutil.rmtree(test_dir, ignore_errors=True)
    os.makedirs(exports_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)

    rerender_queue_file = os.path.join(data_dir, "rerender_queue.json")
    rerender_jobs_file = os.path.join(data_dir, "rerender_jobs.json")
    queue_entries_path = os.path.join(data_dir, "queue_entries.json")

    with open(rerender_queue_file, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)

    with open(rerender_jobs_file, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)

    queue_store = QueueStore(queue_entries_path=queue_entries_path)
    queue_store.create_queue_entry(
        QueueEntry(
            queue_entry_id="queue_ops_001",
            dedupe_key="queue_ops_dedupe_001",
            source_review_view_id="review_ops_001",
            source_opportunity_id="opp_ops_001",
            source_signal_id="signal_ops_001",
            topic_label="Operations Topic Strong",
            platform="youtube",
            channel_type="gaming_main",
            channel_group="gaming",
            content_kind="longform",
            queue_state=QueueState.QUEUED,
            opportunity_score=84.2,
            opportunity_level=OpportunityLevel.HIGH,
            lifespan_class=LifespanClass.SHORT,
            review_status=OpportunityReviewStatus.APPROVED,
            review_summary="Strong operations candidate",
            block_reason=None,
        )
    )

    storage = LocalStorageProvider()
    service = OperationsDashboardService(storage_provider=storage)
    service.jarvis_status_service.queue_store = queue_store
    service.jarvis_status_service.runtime_mode_controller = service.jarvis_status_service.runtime_mode_controller.__class__(
        state_path=os.path.join(data_dir, "runtime_mode.json")
    )
    service.jarvis_status_service.vacation_controller = service.jarvis_status_service.vacation_controller.__class__(
        state_path=os.path.join(data_dir, "vacation_state.json")
    )

    surface = service.build_operations_surface(
        base_path=exports_dir,
        rerender_queue_file=rerender_queue_file,
        rerender_jobs_file=rerender_jobs_file,
    )

    assert "overview" in surface
    assert "queue" in surface
    assert "publish" in surface
    assert "maintenance" in surface
    assert "jarvis_panel" in surface

    assert isinstance(surface["overview"]["cards"], list)
    assert surface["queue"]["total_entries"] == 1
    assert surface["queue"]["blocked_count"] == 0
    assert isinstance(surface["warnings"]["warning_cases"], list)
    assert isinstance(surface["jarvis_panel"]["example_commands"], list)

    print("OPERATIONS DASHBOARD SERVICE SMOKE TEST PASSED")
    print(
        {
            "overview_cards": len(surface["overview"]["cards"]),
            "queue_total_entries": surface["queue"]["total_entries"],
            "warning_count": surface["warnings"]["warning_count"],
            "maintenance_integrity_issue_count": surface["maintenance"]["integrity_issue_count"],
        }
    )


if __name__ == "__main__":
    main()