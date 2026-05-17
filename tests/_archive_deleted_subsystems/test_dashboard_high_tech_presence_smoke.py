from dashboard import app


def main() -> None:
    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Jarvis Presence Core" in html
    assert "JARVIS" in html
    assert "System Signal Ribbon" in html
    assert "State:" in html
    assert "Alert:" in html
    assert "Focus:" in html

    print("DASHBOARD HIGH TECH PRESENCE SMOKE TEST PASSED")
    print(
        {
            "status_code": response.status_code,
            "has_presence_core": "Jarvis Presence Core" in html,
            "has_jarvis_title": "JARVIS" in html,
            "has_signal_ribbon": "System Signal Ribbon" in html,
        }
    )


if __name__ == "__main__":
    main()