from core.jarvis_presence_service import JarvisPresenceService


def main() -> None:
    service = JarvisPresenceService()
    payload = service.build_presence_surface()

    assert "theme" in payload
    assert "presence" in payload
    assert "operations" in payload

    presence = payload["presence"]

    assert presence["title"] == "JARVIS"
    assert "Runtime" in presence["status_line"]
    assert isinstance(presence["highlight_metrics"], list)

    print("JARVIS PRESENCE SERVICE SMOKE TEST PASSED")
    print(
        {
            "title": presence["title"],
            "presence_state": presence["presence_state"],
            "alert_level": presence["alert_level"],
            "focus_label": presence["focus_label"],
        }
    )


if __name__ == "__main__":
    main()