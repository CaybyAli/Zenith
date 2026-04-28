from __future__ import annotations

from typing import Any

from core.workspace_repository import WorkspaceRepository
from models.actor_context import ActorContext
from shared.errors import NotFoundError
from shared.role_enums import RoleType


class AccessContextService:
    def __init__(
        self,
        workspace_repository: WorkspaceRepository | None = None,
    ) -> None:
        self.workspace_repository = workspace_repository or WorkspaceRepository()

    def resolve_actor_context(
        self,
        *,
        actor_id: str | None = None,
        workspace_id: str | None = None,
        display_name: str | None = None,
        is_remote: bool = False,
    ) -> ActorContext:
        default_workspace = self.workspace_repository.ensure_default_workspace()

        normalized_workspace_id = (
            str(workspace_id).strip()
            if workspace_id is not None and str(workspace_id).strip()
            else default_workspace.workspace_id
        )
        normalized_actor_id = (
            str(actor_id).strip()
            if actor_id is not None and str(actor_id).strip()
            else default_workspace.owner_actor_id
        )
        normalized_display_name = (
            str(display_name).strip()
            if display_name is not None and str(display_name).strip()
            else normalized_actor_id
        )

        try:
            membership = self.workspace_repository.get_membership(
                normalized_actor_id,
                normalized_workspace_id,
            )
            role = membership.role
        except NotFoundError:
            role = RoleType.READ_ONLY

        return ActorContext(
            actor_id=normalized_actor_id,
            role=role,
            workspace_id=normalized_workspace_id,
            display_name=normalized_display_name,
            is_remote=bool(is_remote),
        )

    def resolve_from_request(self, request) -> ActorContext:
        actor_id = self._extract_request_value(
            request,
            "zenith_actor_id",
            "actor_id",
        )
        workspace_id = self._extract_request_value(
            request,
            "zenith_workspace_id",
            "workspace_id",
        )
        display_name = self._extract_request_value(
            request,
            "zenith_display_name",
            "display_name",
        )
        remote_raw = self._extract_request_value(
            request,
            "zenith_remote",
            "remote",
        )

        is_remote = self._normalize_bool(remote_raw)

        return self.resolve_actor_context(
            actor_id=actor_id,
            workspace_id=workspace_id,
            display_name=display_name,
            is_remote=is_remote,
        )

    def _extract_request_value(self, request, *keys: str) -> str | None:
        containers: list[Any] = []

        args = getattr(request, "args", None)
        form = getattr(request, "form", None)
        headers = getattr(request, "headers", None)

        if args is not None:
            containers.append(args)
        if form is not None:
            containers.append(form)
        if headers is not None:
            containers.append(headers)

        for key in keys:
            for container in containers:
                try:
                    value = container.get(key)
                except Exception:
                    value = None

                if value is None:
                    continue

                normalized = str(value).strip()
                if normalized:
                    return normalized

        return None

    def _normalize_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value

        normalized = str(value or "").strip().lower()
        return normalized in {"1", "true", "yes", "on", "remote"}