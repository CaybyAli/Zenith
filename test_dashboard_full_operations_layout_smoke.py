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
    assert "<th>Job</th>" in html
    assert "<th>Channel</th>" in html
    assert "<th>Review</th>" in html
    assert "<th>Publish</th>" in html
    assert "<th>Action</th>" in html
    assert "Rerender Jobs" in html

    print("DASHBOARD FULL OPERATIONS LAYOUT SMOKE TEST PASSED")
    print(
        {
            "status_code": response.status_code,
            "has_unified_operations": "Unified Operations Overview" in html,
            "has_publish_and_guards": "Publish & Guards" in html,
            "has_review_table": "<th>Job</th>" in html and "<th>Action</th>" in html,
            "has_rerender_jobs": "Rerender Jobs" in html,
        }
    )


if __name__ == "__main__":
    main()