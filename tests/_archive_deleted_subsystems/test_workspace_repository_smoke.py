from __future__ import annotations

import os
import shutil

from core.workspace_repository import WorkspaceRepository
from models.workspace import Workspace
from models.workspace_membership import WorkspaceMembership
from shared.role_enums import RoleType


def main() -> None:
    test_dir = "tmp/workspace_repository_test"
    data_dir = os.path.join(test_dir, "data")
    workspaces_path = os.path.join(data_dir, "workspaces.json")

    shutil.rmtree(test_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)

    repo = WorkspaceRepository(workspaces_path=workspaces_path)

    workspace = repo.create_workspace(
        Workspace(
            workspace_id="ws_test",
            workspace_name="Workspace Test",
            owner_actor_id="owner_test",
            enabled=True,
        )
    )

    repo.upsert_membership(
        WorkspaceMembership(
            actor_id="owner_test",
            workspace_id="ws_test",
            role=RoleType.OWNER,
            enabled=True,
        )
    )
    repo.upsert_membership(
        WorkspaceMembership(
            actor_id="reviewer_test",
            workspace_id="ws_test",
            role=RoleType.REVIEWER,
            enabled=True,
        )
    )

    loaded_workspace = repo.get_workspace("ws_test")
    memberships = repo.list_memberships(workspace_id="ws_test")

    default_workspace = repo.ensure_default_workspace(
        workspace_id="ws_main",
        workspace_name="Zenith Main Workspace",
        owner_actor_id="owner_local",
    )
    default_membership = repo.get_membership("owner_local", "ws_main")

    assert workspace.workspace_id == "ws_test"
    assert loaded_workspace.workspace_name == "Workspace Test"
    assert len(memberships) == 2
    assert default_workspace.workspace_id == "ws_main"
    assert default_membership.role == RoleType.OWNER

    print("WORKSPACE REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "workspace_id": loaded_workspace.workspace_id,
            "workspace_name": loaded_workspace.workspace_name,
            "memberships": len(memberships),
            "default_workspace": default_workspace.workspace_id,
            "default_owner_role": default_membership.role.value,
        }
    )


if __name__ == "__main__":
    main()