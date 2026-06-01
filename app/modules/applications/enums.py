from enum import Enum

class ApplicationStatus(str, Enum):
    SUBMITTED = "Submitted"
    CREDENTIALING_REVIEW = "Credentialing Review"  # Shortlisted state
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
