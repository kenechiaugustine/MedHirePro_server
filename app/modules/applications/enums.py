from enum import Enum

class ApplicationStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    CREDENTIALING_REVIEW = "CREDENTIALING_REVIEW"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.upper().replace(" ", "_")
            for member in cls:
                if member.value == val_upper or member.name == val_upper:
                    return member
        return None
