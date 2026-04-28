from __future__ import annotations

from enum import Enum


class RoleType(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    REVIEWER = "reviewer"
    OPERATOR = "operator"
    READ_ONLY = "read_only"


class ProtectedAction(str, Enum):
    VIEW_DASHBOARD = "view_dashboard"
    USE_JARVIS = "use_jarvis"

    REVIEW_DECISION = "review_decision"
    SHORT_REVIEW_DECISION = "short_review_decision"

    PUBLISH_VIDEO = "publish_video"
    PUBLISH_SHORTS = "publish_shorts"

    RERENDER = "rerender"
    REPOST = "repost"

    SET_RUNTIME_MODE = "set_runtime_mode"
    SET_VACATION_STATE = "set_vacation_state"

    RUN_MAINTENANCE = "run_maintenance"

    REMOTE_CONTROL = "remote_control"