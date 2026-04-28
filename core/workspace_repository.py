from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.workspace import Workspace
from models.workspace_membership import WorkspaceMembership
from shared.errors import NotFoundError, StorageError
from shared.role_enums import RoleType


class WorkspaceRepository:
    def __init__(
        self,
        workspaces_path: str = "data/workspaces.json",
    ) -> None:
        self.workspaces_path = Path(workspaces_path)
        self.workspaces_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.workspaces_path.exists():
            self._write_raw(
                {
                    "workspaces": {},
                    "memberships": [],
                }
            )

    def create_workspace(self, workspace: Workspace) -> Workspace:
        data = self._read_raw()
        workspaces = data["workspaces"]

        if workspace.workspace_id in workspaces:
            raise StorageError(f"Workspace already exists: {workspace.workspace_id}")

        workspaces[workspace.workspace_id] = workspace.to_dict()
        self._write_raw(data)
        return workspace

    def update_workspace(self, workspace: Workspace) -> Workspace:
        data = self._read_raw()
        workspaces = data["workspaces"]

        if workspace.workspace_id not in workspaces:
            raise NotFoundError(f"Workspace not found: {workspace.workspace_id}")

        workspace.touch()
        workspaces[workspace.workspace_id] = workspace.to_dict()
        self._write_raw(data)
        return workspace

    def get_workspace(self, workspace_id: str) -> Workspace:
        data = self._read_raw()
        workspaces = data["workspaces"]

        if workspace_id not in workspaces:
            raise NotFoundError(f"Workspace not found: {workspace_id}")

        return Workspace.from_dict(workspaces[workspace_id])

    def list_workspaces(self) -> list[Workspace]:
        data = self._read_raw()
        return [
            Workspace.from_dict(item)
            for item in data.get("workspaces", {}).values()
            if isinstance(item, dict)
        ]

    def upsert_membership(self, membership: WorkspaceMembership) -> WorkspaceMembership:
        data = self._read_raw()
        memberships = data["memberships"]

        for index, item in enumerate(memberships):
            if not isinstance(item, dict):
                continue

            existing = WorkspaceMembership.from_dict(item)
            if (
                existing.actor_id == membership.actor_id
                and existing.workspace_id == membership.workspace_id
            ):
                membership.touch()
                memberships[index] = membership.to_dict()
                self._write_raw(data)
                return membership

        memberships.append(membership.to_dict())
        self._write_raw(data)
        return membership

    def get_membership(
        self,
        actor_id: str,
        workspace_id: str,
    ) -> WorkspaceMembership:
        data = self._read_raw()

        for item in data.get("memberships", []):
            if not isinstance(item, dict):
                continue

            membership = WorkspaceMembership.from_dict(item)
            if membership.actor_id == actor_id and membership.workspace_id == workspace_id:
                return membership

        raise NotFoundError(
            f"Workspace membership not found: actor_id={actor_id}, workspace_id={workspace_id}"
        )

    def list_memberships(
        self,
        *,
        workspace_id: str | None = None,
        actor_id: str | None = None,
    ) -> list[WorkspaceMembership]:
        data = self._read_raw()
        memberships: list[WorkspaceMembership] = []

        for item in data.get("memberships", []):
            if not isinstance(item, dict):
                continue

            membership = WorkspaceMembership.from_dict(item)

            if workspace_id is not None and membership.workspace_id != workspace_id:
                continue

            if actor_id is not None and membership.actor_id != actor_id:
                continue

            memberships.append(membership)

        return memberships

    def ensure_default_workspace(
        self,
        *,
        workspace_id: str = "ws_main",
        workspace_name: str = "Zenith Main Workspace",
        owner_actor_id: str = "owner_local",
    ) -> Workspace:
        try:
            workspace = self.get_workspace(workspace_id)
        except NotFoundError:
            workspace = self.create_workspace(
                Workspace(
                    workspace_id=workspace_id,
                    workspace_name=workspace_name,
                    owner_actor_id=owner_actor_id,
                    enabled=True,
                )
            )

        self.upsert_membership(
            WorkspaceMembership(
                actor_id=owner_actor_id,
                workspace_id=workspace.workspace_id,
                role=RoleType.OWNER,
                enabled=True,
            )
        )
        return workspace

    def _read_raw(self) -> dict[str, Any]:
        try:
            with self.workspaces_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise StorageError(f"Could not read workspace repository: {exc}") from exc

    def _write_raw(self, data: dict[str, Any]) -> None:
        try:
            with self.workspaces_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise StorageError(f"Could not write workspace repository: {exc}") from exc