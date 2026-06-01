from datetime import datetime, timezone
from typing import Optional
from app.modules.user.enums import UserRole

class UserModel:
    @staticmethod
    def new_user(
        email: str,
        role: UserRole,
        password_hash: Optional[str] = None,
        full_name: Optional[str] = None,
        specialty: Optional[str] = None,
        facility_name: Optional[str] = None,
        google_id: Optional[str] = None,
        avatar_url: Optional[str] = None,
        employment_status: Optional[str] = None,
        current_workplace: Optional[str] = None,
        referral_code: Optional[str] = None,
        referred_by: Optional[str] = None,
    ) -> dict:
        return {
            "email": email,
            "password_hash": password_hash,     # Nullable for Google users
            "full_name": full_name,
            "specialty": specialty,             # For professionals
            "facility_name": facility_name,     # For institutes
            "google_id": google_id,             # Nullable for Email/Pass users
            "avatar_url": avatar_url,
            "role": role,
            "credit_balance": 2,                # Default welcome bonus
            "daily_credit_cap": 20,             # Default cap per user
            "is_active": True,
            "is_deleted": False,
            "onboarding_status": "not_started",
            "is_verified": False,
            "employment_status": employment_status,
            "current_workplace": current_workplace,
            "referral_code": referral_code,
            "referred_by": referred_by,
            "referred_count": 0,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }