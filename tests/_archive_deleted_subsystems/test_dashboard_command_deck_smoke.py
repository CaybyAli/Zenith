from dashboard import app


def main() -> None:
    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Zenith Command Deck" in html
    assert 'href="#access-context"' in html
    assert 'href="#operations-overview"' in html
    assert 'href="#roles-permissions"' in html
    assert 'href="#publish-guards"' in html
    assert 'href="#system-control"' in html
    assert 'href="#kpi-surface"' in html
    assert 'href="#feedback-surface"' in html
    assert 'href="#review-grid"' in html
    assert 'href="#rerender-jobs"' in html

    print("DASHBOARD COMMAND DECK SMOKE TEST PASSED")
    print(
        {
            "status_code": response.status_code,
            "has_command_deck": "Zenith Command Deck" in html,
            "has_access_anchor": 'href="#access-context"' in html,
            "has_review_anchor": 'href="#review-grid"' in html,
            "has_rerender_anchor": 'href="#rerender-jobs"' in html,
        }
    )


if __name__ == "__main__":
    main()