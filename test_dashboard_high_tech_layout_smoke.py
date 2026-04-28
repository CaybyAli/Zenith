from dashboard import app


def main() -> None:
    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Jarvis Presence Core" in html
    assert "JARVIS" in html
    assert "System Signal Ribbon" in html
    assert "Zenith Command Deck" in html

    assert "Access Context" in html
    assert "Unified Operations Overview" in html
    assert "Roles & Permissions" in html
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

    assert 'href="#access-context"' in html
    assert 'href="#operations-overview"' in html
    assert 'href="#roles-permissions"' in html
    assert 'href="#publish-guards"' in html
    assert 'href="#system-control"' in html
    assert 'href="#kpi-surface"' in html
    assert 'href="#feedback-surface"' in html
    assert 'href="#review-grid"' in html
    assert 'href="#rerender-jobs"' in html

    print("DASHBOARD HIGH TECH LAYOUT SMOKE TEST PASSED")
    print(
        {
            "status_code": response.status_code,
            "has_presence_core": "Jarvis Presence Core" in html,
            "has_command_deck": "Zenith Command Deck" in html,
            "has_unified_operations": "Unified Operations Overview" in html,
            "has_roles_permissions": "Roles & Permissions" in html,
            "has_review_table": "<th>Job</th>" in html and "<th>Action</th>" in html,
            "has_rerender_jobs": "Rerender Jobs" in html,
        }
    )


if __name__ == "__main__":
    main()