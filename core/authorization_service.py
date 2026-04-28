from __future__ import annotations

from models.actor_context import ActorContext
from shared.role_enums import ProtectedAction, RoleType


class AuthorizationService:
    _ROLE_ACTIONS: dict[RoleType, set[ProtectedAction]] = {
        RoleType.OWNER: {
            ProtectedAction.VIEW_DASHBOARD,
            ProtectedAction.USE_JARVIS,
            ProtectedAction.REVIEW_DECISION,
            ProtectedAction.SHORT_REVIEW_DECISION,
            ProtectedAction.PUBLISH_VIDEO,
            ProtectedAction.PUBLISH_SHORTS,
            ProtectedAction.RERENDER,
            ProtectedAction.REPOST,
            ProtectedAction.SET_RUNTIME_MODE,
            ProtectedAction.SET_VACATION_STATE,
            ProtectedAction.RUN_MAINTENANCE,
            ProtectedAction.REMOTE_CONTROL,
        },
        RoleType.ADMIN: {
            ProtectedAction.VIEW_DASHBOARD,
            ProtectedAction.USE_JARVIS,
            ProtectedAction.REVIEW_DECISION,
            ProtectedAction.SHORT_REVIEW_DECISION,
            ProtectedAction.PUBLISH_VIDEO,
            ProtectedAction.PUBLISH_SHORTS,
            ProtectedAction.RERENDER,
            ProtectedAction.REPOST,
            ProtectedAction.SET_RUNTIME_MODE,
            ProtectedAction.SET_VACATION_STATE,
            ProtectedAction.RUN_MAINTENANCE,
            ProtectedAction.REMOTE_CONTROL,
        },
        RoleType.REVIEWER: {
            ProtectedAction.VIEW_DASHBOARD,
            ProtectedAction.USE_JARVIS,
            ProtectedAction.REVIEW_DECISION,
            ProtectedAction.SHORT_REVIEW_DECISION,
        },
        RoleType.OPERATOR: {
            ProtectedAction.VIEW_DASHBOARD,
            ProtectedAction.USE_JARVIS,
            ProtectedAction.PUBLISH_VIDEO,
            ProtectedAction.PUBLISH_SHORTS,
            ProtectedAction.RERENDER,
            ProtectedAction.REPOST,
            ProtectedAction.SET_RUNTIME_MODE,
            ProtectedAction.SET_VACATION_STATE,
            ProtectedAction.RUN_MAINTENANCE,
        },
        RoleType.READ_ONLY: {
            ProtectedAction.VIEW_DASHBOARD,
            ProtectedAction.USE_JARVIS,
        },
    }

    def can_execute(
        self,
        actor: ActorContext,
        action: ProtectedAction,
        *,
        workspace_id: str | None = None,
    ) -> bool:
        allowed_actions = self._ROLE_ACTIONS.get(actor.role, set())
        if action not in allowed_actions:
            return False

        if workspace_id is not None:
            actor_workspace = (actor.workspace_id or "").strip()
            target_workspace = str(workspace_id).strip()

            if not actor_workspace or actor_workspace != target_workspace:
                return False

        return True

    def assert_allowed(
        self,
        actor: ActorContext,
        action: ProtectedAction,
        *,
        workspace_id: str | None = None,
    ) -> None:
        if not self.can_execute(actor, action, workspace_id=workspace_id):
            raise PermissionError(
                f"Actor '{actor.actor_id}' with role '{actor.role.value}' "
                f"is not allowed to execute '{action.value}'"
            )

    def can_view_dashboard(
        self,
        actor: ActorContext,
        *,
        workspace_id: str | None = None,
    ) -> bool:
        return self.can_execute(
            actor,
            ProtectedAction.VIEW_DASHBOARD,
            workspace_id=workspace_id,
        )

    def can_use_jarvis(
        self,
        actor: ActorContext,
        *,
        workspace_id: str | None = None,
    ) -> bool:
        return self.can_execute(
            actor,
            ProtectedAction.USE_JARVIS,
            workspace_id=workspace_id,
        )

    def get_allowed_actions_for_role(
        self,
        role: RoleType,
    ) -> list[ProtectedAction]:
        return sorted(
            self._ROLE_ACTIONS.get(role, set()),
            key=lambda item: item.value,
        )

    def build_role_capability_matrix(self) -> list[dict[str, object]]:
        matrix: list[dict[str, object]] = []

        for role in RoleType:
            allowed_actions = self.get_allowed_actions_for_role(role)
            matrix.append(
                {
                    "role": role.value,
                    "allowed_action_count": len(allowed_actions),
                    "allowed_actions": [action.value for action in allowed_actions],
                }
            )

        return matrix