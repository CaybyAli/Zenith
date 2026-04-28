from dashboard import app


def main() -> None:
    client = app.test_client()

    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    assert "Roles & Permissions" in html
    assert "Role Capability Matrix" in html
    assert "owner" in html
    assert "admin" in html
    assert "reviewer" in html
    assert "operator" in html
    assert "read_only" in html

    print("DASHBOARD ROLES PERMISSIONS SURFACE SMOKE TEST PASSED")
    print(
        {
            "status_code": response.status_code,
            "has_roles_permissions": "Roles & Permissions" in html,
            "has_owner": "owner" in html,
            "has_reviewer": "reviewer" in html,
            "has_read_only": "read_only" in html,
        }
    )


if __name__ == "__main__":
    main()