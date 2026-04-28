from dashboard import app


def main() -> None:
    client = app.test_client()

    response = client.post(
        "/jarvis_command",
        data={"jarvis_query": "Wie ist der Systemstatus?"},
        headers={
            "zenith_actor_id": "reviewer_remote",
            "zenith_workspace_id": "ws_main",
            "zenith_display_name": "Remote Reviewer",
            "zenith_remote": "true",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Access Context" in html
    assert "reviewer_remote" in html
    assert "reviewer" in html
    assert "ws_main" in html
    assert "true" in html

    print("DASHBOARD ACCESS CONTEXT SURFACE SMOKE TEST PASSED")
    print(
        {
            "status_code": response.status_code,
            "has_access_context": "Access Context" in html,
            "has_actor_id": "reviewer_remote" in html,
            "has_role": "reviewer" in html,
            "has_workspace": "ws_main" in html,
        }
    )


if __name__ == "__main__":
    main()