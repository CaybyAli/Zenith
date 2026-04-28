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
    original_build_surface = dashboard.kpi_dashboard_service.build_surface

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
            "total_entries": 2,
            "winner_count": 1,
            "loser_count": 1,
            "outlier_count": 0,
            "entries": [],
            "top_entries": [
                {
                    "variant_id": "variant_dash_ui_001",
                    "target_platform": "youtube",
                    "performance_score": 84.3,
                    "comparison_status": "above_average",
                }
            ],
            "low_entries": [
                {
                    "variant_id": "variant_dash_ui_002",
                    "target_platform": "tiktok",
                    "performance_score": 28.1,
                    "comparison_status": "below_average",
                }
            ],
            "comparison_summaries": [],
            "insights": [
                {
                    "title": "Top performer detected",
                    "summary_text": "Variant variant_dash_ui_001 leads the current KPI surface.",
                    "severity": "info",
                }
            ],
            "platform_stats": [
                {
                    "platform": "youtube",
                    "entry_count": 1,
                    "average_score": 84.3,
                    "top_variant_id": "variant_dash_ui_001",
                    "top_score": 84.3,
                }
            ],
            "channel_stats": [
                {
                    "channel": "gaming_main",
                    "entry_count": 1,
                    "average_score": 84.3,
                    "top_variant_id": "variant_dash_ui_001",
                    "top_score": 84.3,
                }
            ],
        }

        with dashboard.app.test_client() as client:
            response = client.get("/")
            html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "KPI Dashboard / Insight Surface" in html
        assert "Total KPI Entries" in html
        assert "Top Performers" in html
        assert "Low Performers" in html
        assert "Platform Comparison" in html
        assert "Channel Comparison" in html
        assert "variant_dash_ui_001" in html
        assert "variant_dash_ui_002" in html
        assert "Top performer detected" in html
        assert "youtube" in html
        assert "gaming_main" in html

        print("DASHBOARD KPI SURFACE RENDER SMOKE TEST PASSED")
        print(
            {
                "status_code": response.status_code,
                "top_variant": "variant_dash_ui_001",
                "low_variant": "variant_dash_ui_002",
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
        dashboard.kpi_dashboard_service.build_surface = original_build_surface


if __name__ == "__main__":
    run()