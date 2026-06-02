from enum import Enum

class OnboardingStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    NOT_STARTED = "not_started"
