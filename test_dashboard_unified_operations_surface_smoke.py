from __future__ import annotations

from dashboard import app


def main() -> None:
    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Unified Operations Overview" in html
    assert "Jarvis Panel" in html
    assert "Queue Status" in html
    assert "Maintenance Status" in html
    assert "Publish & Guards" in html
    assert "System Control" in html
    assert "KPI Dashboard / Insight Surface" in html
    assert "Feedback Learning Backbone" in html

    print("DASHBOARD UNIFIED OPERATIONS SURFACE SMOKE TEST PASSED")
    print(
        {
            "status_code": response.status_code,
            "has_unified_operations": "Unified Operations Overview" in html,
            "has_jarvis_panel": "Jarvis Panel" in html,
            "has_queue_status": "Queue Status" in html,
            "has_maintenance_status": "Maintenance Status" in html,
            "has_publish_and_guards": "Publish & Guards" in html,
        }
    )


if __name__ == "__main__":
    main()