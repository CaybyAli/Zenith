from __future__ import annotations

import os
import shutil

from core.access_context_service import AccessContextService
from core.workspace_repository import WorkspaceRepository
from models.workspace_membership import WorkspaceMembership
from shared.role_enums import RoleType


def main() -> None:
    test_dir = "tmp/access_context_service_test"
    data_dir = os.path.join(test_dir, "data")
    workspaces_path = os.path.join(data_dir, "workspaces.json")

    shutil.rmtree(test_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)

    repo = WorkspaceRepository(workspaces_path=workspaces_path)
    repo.ensure_default_workspace(
        workspace_id="ws_main",
        workspace_name="Zenith Main Workspace",
        owner_actor_id="owner_local",
    )
    repo.upsert_membership(
        WorkspaceMembership(
            actor_id="reviewer_remote",
            workspace_id="ws_main",
            role=RoleType.REVIEWER,
            enabled=True,
        )
    )

    service = AccessContextService(workspace_repository=repo)

    default_actor = service.resolve_actor_context()
    reviewer_actor = service.resolve_actor_context(
        actor_id="reviewer_remote",
        workspace_id="ws_main",
        display_name="Remote Reviewer",
        is_remote=True,
    )
    unknown_actor = service.resolve_actor_context(
        actor_id="unknown_remote",
        workspace_id="ws_main",
        display_name="Unknown Remote",
        is_remote=True,
    )

    assert default_actor.actor_id == "owner_local"
    assert default_actor.role == RoleType.OWNER
    assert default_actor.workspace_id == "ws_main"

    assert reviewer_actor.actor_id == "reviewer_remote"
    assert reviewer_actor.role == RoleType.REVIEWER
    assert reviewer_actor.is_remote is True

    assert unknown_actor.actor_id == "unknown_remote"
    assert unknown_actor.role == RoleType.READ_ONLY
    assert unknown_actor.is_remote is True

    print("ACCESS CONTEXT SERVICE SMOKE TEST PASSED")
    print(
        {
            "default_actor": default_actor.to_dict(),
            "reviewer_actor": reviewer_actor.to_dict(),
            "unknown_actor": unknown_actor.to_dict(),
        }
    )


if __name__ == "__main__":
    main()