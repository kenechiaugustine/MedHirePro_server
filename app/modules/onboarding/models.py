from datetime import datetime, timezone
from bson import ObjectId
from app.modules.onboarding.enums import OnboardingStatus

class OnboardingSubmissionModel:
    @staticmethod
    def new_submission(
        user_id: ObjectId,
        role: str,
        details: dict,
    ) -> dict:
        return {
            "user_id": user_id,
            "role": role,
            "details": details,
            "status": OnboardingStatus.PENDING.value,
            "submitted_at": datetime.now(timezone.utc),
            "reviewed_at": None,
            "reviewed_by": None,
            "rejection_reason": None
        }
