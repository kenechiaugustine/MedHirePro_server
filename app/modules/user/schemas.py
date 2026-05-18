from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.modules.user.enums import UserRole

# Base User Schema
class UserBase(BaseModel):
    email: EmailStr = Field(..., examples=["kenechiaugustine@yopmail.com"])

# Registration - Professional
class ProfessionalRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=72, description="Password must be between 8 and 72 characters")
    full_name: str
    specialty: str

# Registration - Institute
class InstituteRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=72, description="Password must be between 8 and 72 characters")
    facility_name: str

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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True