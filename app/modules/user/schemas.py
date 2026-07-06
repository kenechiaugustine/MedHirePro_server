from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.modules.user.enums import UserRole, EmploymentStatus
from app.modules.onboarding.schemas import FacilityAddress

# Base User Schema
class UserBase(BaseModel):
    email: EmailStr = Field(..., examples=["kenechiaugustine@yopmail.com"])

# Registration - Professional
class ProfessionalRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=72, description="Password must be between 8 and 72 characters")
    full_name: str
    specialty: str
    employment_status: Optional[EmploymentStatus] = None
    current_workplace: Optional[str] = None
    referred_by_code: Optional[str] = None

# Registration - Institute
class InstituteRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=72, description="Password must be between 8 and 72 characters")
    facility_name: str
    referred_by_code: Optional[str] = None

# Login Payload
class UserLogin(UserBase):
    password: str = Field(..., max_length=72, description="Password must not exceed 72 characters")

# Credit Update Payload
class UserUpdateCredits(BaseModel):
    amount: int
    operation: str  # "add" or "subtract"

# Profile Update Payload
class UserUpdateProfile(BaseModel):
    full_name: Optional[str] = None
    specialty: Optional[str] = None
    facility_name: Optional[str] = None
    avatar_url: Optional[str] = None
    employment_status: Optional[EmploymentStatus] = None
    current_workplace: Optional[str] = None

# Response Schema
class UserResponse(UserBase):
    id: str = Field(alias="_id")
    full_name: Optional[str] = None
    specialty: Optional[str] = None
    facility_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole
    credit_balance: int
    daily_credit_cap: int = 20
    is_active: bool
    is_deleted: bool = False
    banned_from_posting: bool = False
    banned_from_applying: bool = False
    onboarding_status: str = "pending"
    is_verified: bool = False
    employment_status: Optional[str] = None
    current_workplace: Optional[str] = None
    is_intern: Optional[bool] = None
    licence_number: Optional[str] = None
    licence_expiry: Optional[str] = None
    licence_document_url: Optional[str] = None
    degree_document_url: Optional[str] = None
    id_document_url: Optional[str] = None
    school_or_placement_letter_url: Optional[str] = None
    business_registration_number: Optional[str] = None
    facility_type: Optional[str] = None
    business_license_url: Optional[str] = None
    proof_of_address_url: Optional[str] = None
    representative_id_url: Optional[str] = None
    facility_address: Optional[FacilityAddress] = None
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None
    referred_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
