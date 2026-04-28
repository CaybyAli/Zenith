from enum import Enum


class RuntimeMode(str, Enum):
    FULL_POWER = "full_power"
    BALANCED = "balanced"
    STREAM_SAFE = "stream_safe"
    GAMING_SAFE = "gaming_safe"
    IDLE_ONLY = "idle_only"
    PAUSED = "paused"


class RuntimeAction(str, Enum):
    DASHBOARD_REVIEW = "dashboard_review"
    MODE_SWITCH = "mode_switch"
    PUBLISH_DISPATCH = "publish_dispatch"
    REPOST_DISPATCH = "repost_dispatch"
    SHORT_RETRY_DISPATCH = "short_retry_dispatch"
    RERENDER_QUEUE_INTAKE = "rerender_queue_intake"
    RERENDER_PIPELINE = "rerender_pipeline"
    CONTENT_PIPELINE = "content_pipeline"
    FACELESS_PIPELINE = "faceless_pipeline"