from core.operations_dashboard_service import OperationsDashboardService


def main() -> None:
    service = OperationsDashboardService()
    surface = service.build_operations_surface()

    assert "access_policy" in surface
    assert "roles" in surface["access_policy"]
    assert isinstance(surface["access_policy"]["roles"], list)
    assert len(surface["access_policy"]["roles"]) >= 5

    role_names = [item["role"] for item in surface["access_policy"]["roles"]]

    assert "owner" in role_names
    assert "admin" in role_names
    assert "reviewer" in role_names
    assert "operator" in role_names
    assert "read_only" in role_names

    print("OPERATIONS ACCESS POLICY SMOKE TEST PASSED")
    print(
        {
            "role_count": surface["access_policy"]["role_count"],
            "roles": role_names,
        }
    )


if __name__ == "__main__":
    main()