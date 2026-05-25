from pydantic import BaseModel, Field
from typing import Optional

class ApplyReferralRequest(BaseModel):
    referral_code: str = Field(..., description="Referral code to apply")

class UserReferralDetailsResponse(BaseModel):
    referral_code: Optional[str] = None
    referred_count: int = 0
    referred_by: Optional[str] = None
    total_referral_credits_earned: int = 0
