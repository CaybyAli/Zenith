from enum import Enum


class OpportunityReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WATCH = "watch"