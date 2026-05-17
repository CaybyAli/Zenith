from core.authorization_service import AuthorizationService
from models.actor_context import ActorContext
from shared.role_enums import ProtectedAction, RoleType


def main() -> None:
    service = AuthorizationService()

    owner = ActorContext(
        actor_id="owner_001",
        role=RoleType.OWNER,
        workspace_id="ws_main",
        display_name="Owner",
        is_remote=False,
    )
    reviewer = ActorContext(
        actor_id="reviewer_001",
        role=RoleType.REVIEWER,
        workspace_id="ws_main",
        display_name="Reviewer",
        is_remote=False,
    )
    read_only = ActorContext(
        actor_id="readonly_001",
        role=RoleType.READ_ONLY,
        workspace_id="ws_main",
        display_name="ReadOnly",
        is_remote=True,
    )

    assert service.can_execute(
        owner,
        ProtectedAction.PUBLISH_VIDEO,
        workspace_id="ws_main",
    ) is True

    assert service.can_execute(
        reviewer,
        ProtectedAction.REVIEW_DECISION,
        workspace_id="ws_main",
    ) is True

    assert service.can_execute(
        reviewer,
        ProtectedAction.PUBLISH_VIDEO,
        workspace_id="ws_main",
    ) is False

    assert service.can_execute(
        read_only,
        ProtectedAction.VIEW_DASHBOARD,
        workspace_id="ws_main",
    ) is True

    assert service.can_execute(
        read_only,
        ProtectedAction.SET_RUNTIME_MODE,
        workspace_id="ws_main",
    ) is False

    assert service.can_execute(
        owner,
        ProtectedAction.PUBLISH_VIDEO,
        workspace_id="other_workspace",
    ) is False

    print("AUTHORIZATION SERVICE SMOKE TEST PASSED")
    print(
        {
            "owner_publish": service.can_execute(
                owner,
                ProtectedAction.PUBLISH_VIDEO,
                workspace_id="ws_main",
            ),
            "reviewer_review": service.can_execute(
                reviewer,
                ProtectedAction.REVIEW_DECISION,
                workspace_id="ws_main",
            ),
            "reviewer_publish": service.can_execute(
                reviewer,
                ProtectedAction.PUBLISH_VIDEO,
                workspace_id="ws_main",
            ),
            "readonly_view": service.can_execute(
                read_only,
                ProtectedAction.VIEW_DASHBOARD,
                workspace_id="ws_main",
            ),
            "readonly_runtime": service.can_execute(
                read_only,
                ProtectedAction.SET_RUNTIME_MODE,
                workspace_id="ws_main",
            ),
        }
    )


if __name__ == "__main__":
    main()