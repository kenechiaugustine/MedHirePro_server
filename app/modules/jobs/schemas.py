from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime
from app.modules.jobs.enums import (
    JobType,
    JobStatus,
    RateType,
    ClinicalSetting,
    ClinicalSpecialty,
)

class PermanentJobListingCreate(BaseModel):
    position_title: str = Field(..., min_length=2, max_length=150, examples=["Attending Physician"])
    clinical_specialty: ClinicalSpecialty
    clinical_setting: ClinicalSetting
    department_unit: str = Field(..., min_length=1, max_length=100, examples=["Emergency Department"])
    description: str = Field(..., min_length=10, description="Scope of practice and job details")
    required_credentials: List[str] = Field(..., description="Credentials needed (e.g. MD, Board Certified)")
    minimum_experience_years: int = Field(..., ge=0)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    rate_type: RateType = Field(..., description="Billing rate period (HOURLY, DAILY, MONTHLY, etc.)")
    rate_amount_min: float = Field(..., ge=0.0)
    rate_amount_max: float = Field(..., ge=0.0)
    currency: str = Field("NGN", min_length=3, max_length=3)
    currency_symbol: str = Field("₦", min_length=1, max_length=10)
    facility_location: str = Field("", max_length=200)

    # Permanent specific fields
    accepts_interns: bool = Field(False, description="Whether position accepts interns")
    rotation_schedule: Optional[str] = None
    fringe_benefits: Optional[List[str]] = Field(default_factory=list)

class LocumJobListingCreate(BaseModel):
    position_title: str = Field(..., min_length=2, max_length=150, examples=["Locum Emergency Weekend Coverage"])
    clinical_specialty: ClinicalSpecialty
    clinical_setting: ClinicalSetting
    department_unit: str = Field(..., min_length=1, max_length=100, examples=["Emergency Department"])
    description: str = Field(..., min_length=10, description="Shift coverage duties")
    required_credentials: List[str] = Field(..., description="Credentials needed")
    minimum_experience_years: int = Field(..., ge=0)
    city: str = Field(..., min_length=2, max_length=100)
    state: str = Field(..., min_length=2, max_length=100)
    country: str = Field(..., min_length=2, max_length=100)
    rate_type: RateType = Field(..., description="Billing rate period (HOURLY, DAILY, etc.)")
    rate_amount_min: float = Field(..., ge=0.0)
    rate_amount_max: float = Field(..., ge=0.0)
    currency: str = Field("NGN", min_length=3, max_length=3)
    currency_symbol: str = Field("₦", min_length=1, max_length=10)
    facility_location: str = Field("", max_length=200)

    # Locum specific fields
    coverage_start_date: datetime
    coverage_end_date: datetime
    shift_hours: str = Field(..., min_length=2, max_length=100)
    malpractice_insurance_provided: bool = Field(False)
    travel_housing_reimbursement: bool = Field(False)
    on_call_requirements: Optional[str] = None

class JobListingUpdate(BaseModel):
    status: Optional[JobStatus] = None
    position_title: Optional[str] = Field(None, min_length=2, max_length=150)
    clinical_specialty: Optional[ClinicalSpecialty] = None
    clinical_setting: Optional[ClinicalSetting] = None
    department_unit: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=10)
    required_credentials: Optional[List[str]] = None
    minimum_experience_years: Optional[int] = Field(None, ge=0)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    rate_type: Optional[RateType] = None
    rate_amount_min: Optional[float] = Field(None, ge=0.0)
    rate_amount_max: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    currency_symbol: Optional[str] = Field(None, min_length=1, max_length=10)
    facility_location: Optional[str] = Field(None, max_length=200)

    # Permanent specific fields
    accepts_interns: Optional[bool] = None
    rotation_schedule: Optional[str] = None
    fringe_benefits: Optional[List[str]] = None

    # Locum specific fields
    coverage_start_date: Optional[datetime] = None
    coverage_end_date: Optional[datetime] = None
    shift_hours: Optional[str] = None
    malpractice_insurance_provided: Optional[bool] = None
    travel_housing_reimbursement: Optional[bool] = None
    on_call_requirements: Optional[str] = None

class PostedByResponse(BaseModel):
    id: str = Field(alias="_id")
    full_name: Optional[str] = None
    facility_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_verified: bool = False

    class Config:
        populate_by_name = True
        from_attributes = True

class JobListingResponse(BaseModel):
    id: str = Field(alias="_id")
    posted_by: Union[PostedByResponse, str]
    poster_type: str
    job_type: JobType
    status: JobStatus
    position_title: str
    clinical_specialty: ClinicalSpecialty
    clinical_setting: ClinicalSetting
    department_unit: str
    description: str
    required_credentials: List[str]
    minimum_experience_years: int
    city: str
    state: str
    country: str
    rate_type: RateType
    rate_amount_min: float
    rate_amount_max: float
    currency: str
    currency_symbol: str
    facility_location: str

    accepts_interns: Optional[bool] = None
    rotation_schedule: Optional[str] = None
    fringe_benefits: List[str] = []

    coverage_start_date: Optional[datetime] = None
    coverage_end_date: Optional[datetime] = None
    shift_hours: Optional[str] = None
    malpractice_insurance_provided: Optional[bool] = None
    travel_housing_reimbursement: Optional[bool] = None
    on_call_requirements: Optional[str] = None
    
    total_applicants: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
