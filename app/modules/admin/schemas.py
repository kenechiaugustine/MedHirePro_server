from pydantic import BaseModel, Field
from typing import Optional
from app.modules.jobs.enums import JobType
from app.modules.user.enums import UserRole, EmploymentStatus
from app.modules.onboarding.enums import OnboardingStatus

class ReassignJobPayload(BaseModel):
    new_owner_id: str = Field(..., description="MongoDB ObjectId of the new owner")
    job_type: JobType = Field(..., description="Type of job (PERMANENT or LOCUM)")

class AdminUserUpdatePayload(BaseModel):
    full_name: Optional[str] = Field(None, description="User's full name")
    specialty: Optional[str] = Field(None, description="Professional's clinical specialty")
    facility_name: Optional[str] = Field(None, description="Institute's facility name")
    avatar_url: Optional[str] = Field(None, description="Secure profile image URL")
    role: Optional[UserRole] = Field(None, description="User role (professional/institute/admin)")
    is_active: Optional[bool] = Field(None, description="Active status of the account")
    is_verified: Optional[bool] = Field(None, description="Verified status for placements")
    credit_balance: Optional[int] = Field(None, description="Current credits balance")
    daily_credit_cap: Optional[int] = Field(None, description="Daily rolled credit limits cap")
    employment_status: Optional[EmploymentStatus] = Field(None, description="Employment status for candidate")
    current_workplace: Optional[str] = Field(None, description="Current clinical workplace location")
    onboarding_status: Optional[OnboardingStatus] = Field(None, description="User's onboarding status (pending/submitted/approved/rejected)")

class FlagJobPayload(BaseModel):
    reason: str = Field(..., min_length=5, description="Reason for flagging/taking down the job listing")
