from __future__ import annotations

import dashboard


class FakeState:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload)


class FakeJobLoader:
    def load_all_jobs(self, base_path: str = "exports"):
        return []


def run() -> None:
    original_job_loader = dashboard.JobLoader
    original_load_rerender_jobs = dashboard.load_rerender_jobs
    original_runtime_get_state = dashboard.runtime_mode_controller.get_state
    original_vacation_get_state = dashboard.vacation_controller.get_state
    original_vacation_is_active_now = dashboard.vacation_controller.is_active_now
    original_kpi_build_surface = dashboard.kpi_dashboard_service.build_surface
    original_feedback_build_surface = dashboard.feedback_dashboard_service.build_surface

    try:
        dashboard.JobLoader = FakeJobLoader
        dashboard.load_rerender_jobs = lambda provider=None: []

        dashboard.runtime_mode_controller.get_state = lambda: FakeState(
            {
                "mode": "balanced",
                "updated_at": "2026-04-15T16:30:00+00:00",
            }
        )
        dashboard.vacation_controller.get_state = lambda: FakeState(
            {
                "enabled": False,
                "start_at": None,
                "end_at": None,
                "updated_at": "2026-04-15T16:30:00+00:00",
            }
        )
        dashboard.vacation_controller.is_active_now = lambda: False

        dashboard.kpi_dashboard_service.build_surface = lambda base_path="exports": {
            "total_entries": 0,
            "winner_count": 0,
            "loser_count": 0,
            "outlier_count": 0,
            "entries": [],
            "top_entries": [],
            "low_entries": [],
            "comparison_summaries": [],
            "insights": [],
            "platform_stats": [],
            "channel_stats": [],
        }

        dashboard.feedback_dashboard_service.build_surface = lambda base_path="exports": {
            "total_records": 3,
            "recent_feedback": [
                {
                    "feedback_category": "subtitle_style",
                    "feedback_direction": "negative",
                    "variant_id": "variant_fb_ui_001",
                    "feedback_text": "Subtitle movement is too hectic.",
                },
                {
                    "feedback_category": "hook",
                    "feedback_direction": "positive",
                    "variant_id": "variant_fb_ui_002",
                    "feedback_text": "Hook was strong and immediate.",
                },
            ],
            "pattern_summaries": [
                {
                    "category": "subtitle_style",
                    "direction": "negative",
                    "item_count": 2,
                },
                {
                    "category": "hook",
                    "direction": "positive",
                    "item_count": 1,
                },
            ],
            "category_stats": [
                {"category": "subtitle_style", "count": 2},
                {"category": "hook", "count": 1},
            ],
            "direction_stats": [
                {"direction": "negative", "count": 2},
                {"direction": "positive", "count": 1},
            ],
        }

        with dashboard.app.test_client() as client:
            response = client.get("/")
            html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "Feedback Learning Backbone" in html
        assert "Total Feedback Records" in html
        assert "Feedback Categories" in html
        assert "Feedback Directions" in html
        assert "Recent Feedback" in html
        assert "Recurring Feedback Patterns" in html
        assert "subtitle_style" in html
        assert "hook" in html
        assert "variant_fb_ui_001" in html
        assert "variant_fb_ui_002" in html

        print("DASHBOARD FEEDBACK SURFACE RENDER SMOKE TEST PASSED")
        print(
            {
                "status_code": response.status_code,
                "total_records": 3,
                "top_category": "subtitle_style",
            }
        )

    finally:
        dashboard.JobLoader = original_job_loader
        dashboard.load_rerender_jobs = original_load_rerender_jobs
        dashboard.runtime_mode_controller.get_state = original_runtime_get_state
        dashboard.vacation_controller.get_state = original_vacation_get_state
        dashboard.vacation_controller.is_active_now = (
            original_vacation_is_active_now
        )
        dashboard.kpi_dashboard_service.build_surface = original_kpi_build_surface
        dashboard.feedback_dashboard_service.build_surface = (
            original_feedback_build_surface
        )


if __name__ == "__main__":
    run()