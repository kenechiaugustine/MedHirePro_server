from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class ProfessionalOnboardingSubmit(BaseModel):
    phone_number: Optional[str] = Field(None, description="Contact phone number of the professional user")
    is_intern: bool = Field(default=False, description="True if the professional is an intern or student without a license")
    licence_number: Optional[str] = Field(None, description="Active medical license registration number")
    licence_expiry: Optional[str] = Field(None, description="License expiration date (YYYY-MM-DD)")
    licence_document_url: Optional[str] = Field(None, description="Secure URL to uploaded medical license certificate")
    degree_document_url: str = Field(..., description="Secure URL to uploaded medical school diploma/degree certificate")
    id_document_url: str = Field(..., description="Secure URL to uploaded government photo ID (Passport, Driver's License)")
    school_or_placement_letter_url: Optional[str] = Field(None, description="Required if is_intern is True. Secure URL to residency placement letter or Dean's letter")
    specialty: str = Field(..., description="Medical specialty or area of training")
    employment_status: Optional[str] = Field(None, description="Current employment status (e.g., unemployed, full-time)")
    current_workplace: Optional[str] = Field(None, description="Current workplace or clinic")

    @field_validator("licence_number", "licence_expiry", "licence_document_url")
    @classmethod
    def validate_licence_fields(cls, v, info):
        # We will do conditional validation inside the service because model-level fields are interdependent.
        # But we can define this validator to ensure clean whitespace.
        if isinstance(v, str):
            return v.strip()
        return v


class FacilityAddress(BaseModel):
    street: str = Field(..., description="Street address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State or Province")
    zip: str = Field(..., description="Zip or Postal code")
    country: str = Field(..., description="Country")


class InstituteOnboardingSubmit(BaseModel):
    phone_number: Optional[str] = Field(None, description="Contact phone number of the facility representative")
    business_registration_number: str = Field(..., description="Corporate identity, EIN or Tax Registration Number")
    facility_type: str = Field(..., description="Type of facility (e.g., Hospital, Clinic, Diagnostic Center, Pharmacy)")
    business_license_url: str = Field(..., description="Secure URL to uploaded business operating license / permit")
    proof_of_address_url: str = Field(..., description="Secure URL to utility bill, tax document, or lease agreement")
    representative_id_url: str = Field(..., description="Secure URL to government-issued photo ID of the authorized representative")
    facility_address: FacilityAddress


class AdminReviewPayload(BaseModel):
    submission_id: str = Field(..., description="ID of the onboarding submission to review")
    action: str = Field(..., description="Action to perform: must be either 'approve' or 'reject'")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection. Required if action is 'reject'")
