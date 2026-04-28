from enum import Enum


class QueueState(str, Enum):
    QUEUED = "queued"
    BLOCKED = "blocked"
    REMOVED = "removed"