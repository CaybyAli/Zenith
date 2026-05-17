from dashboard import app, runtime_mode_controller


def main() -> None:
    client = app.test_client()

    runtime_mode_controller.set_mode("full_power")

    blocked_response = client.post(
        "/set_runtime_mode/balanced",
        headers={
            "zenith_actor_id": "unknown_remote",
            "zenith_workspace_id": "ws_main",
            "zenith_remote": "true",
        },
        follow_redirects=False,
    )

    assert blocked_response.status_code in {302, 303}
    assert runtime_mode_controller.get_mode().value == "full_power"

    allowed_response = client.post(
        "/set_runtime_mode/balanced",
        headers={
            "zenith_actor_id": "owner_local",
            "zenith_workspace_id": "ws_main",
        },
        follow_redirects=False,
    )

    assert allowed_response.status_code in {302, 303}
    assert runtime_mode_controller.get_mode().value == "balanced"

    jarvis_response = client.post(
        "/jarvis_command",
        data={"jarvis_query": "Wie ist der Systemstatus?"},
        headers={
            "zenith_actor_id": "unknown_remote",
            "zenith_workspace_id": "ws_main",
            "zenith_remote": "true",
        },
        follow_redirects=True,
    )

    assert jarvis_response.status_code == 200
    html = jarvis_response.get_data(as_text=True)

    assert "Jarvis Panel" in html
    assert "Zenith Systemstatus" in html

    runtime_mode_controller.set_mode("full_power")

    print("DASHBOARD ROLE GUARD SMOKE TEST PASSED")
    print(
        {
            "blocked_runtime_change": True,
            "allowed_owner_runtime_change": True,
            "readonly_jarvis_access": True,
        }
    )


if __name__ == "__main__":
    main()