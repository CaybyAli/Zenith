from __future__ import annotations

from dashboard import app


def main() -> None:
    client = app.test_client()

    response = client.post(
        "/jarvis_command",
        data={"jarvis_query": "Wie ist der Systemstatus?"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Jarvis Panel" in html
    assert "Zenith Systemstatus" in html
    assert "Runtime =" in html

    print("DASHBOARD JARVIS PANEL SMOKE TEST PASSED")
    print(
        {
            "status_code": response.status_code,
            "has_jarvis_panel": "Jarvis Panel" in html,
            "has_system_title": "Zenith Systemstatus" in html,
            "has_runtime_summary": "Runtime =" in html,
        }
    )


if __name__ == "__main__":
    main()