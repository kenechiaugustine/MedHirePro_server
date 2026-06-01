from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.modules.jobs.enums import (
    JobType,
    JobStatus,
    RateType,
    ClinicalSetting,
    ClinicalSpecialty,
)

class JobListingModel:
    """
    Unified model definition for Job Listings (both PERMANENT and LOCUM types).
    Contains structural details, geolocation, rate parameters, and role constraints.
    """
    @staticmethod
    def new_job_listing(
        posted_by: str,
        poster_type: str,                       # "institute", "professional", "admin"
        job_type: JobType,                      # "PERMANENT" or "LOCUM"
        position_title: str,
        clinical_specialty: ClinicalSpecialty,
        clinical_setting: ClinicalSetting,
        department_unit: str,
        description: str,                       # Unified field for job details/scope
        required_credentials: List[str],
        minimum_experience_years: int,
        city: str,
        state: str,
        country: str,
        rate_type: RateType,
        rate_amount_min: float,
        rate_amount_max: float,
        currency: str = "NGN",
        currency_symbol: str = "₦",
        status: JobStatus = JobStatus.OPEN,
        
        # Optional fields based on job_type
        accepts_interns: Optional[bool] = None, # Applicable/Required for PERMANENT
        facility_location: str = "",
        
        # Locum specific fields
        coverage_start_date: Optional[datetime] = None,
        coverage_end_date: Optional[datetime] = None,
        shift_hours: Optional[str] = None,
        malpractice_insurance_provided: Optional[bool] = None,
        travel_housing_reimbursement: Optional[bool] = None,
        on_call_requirements: Optional[str] = None,
        
        # Permanent specific fields
        rotation_schedule: Optional[str] = None,
        fringe_benefits: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        doc = {
            "posted_by": posted_by,
            "poster_type": poster_type,
            "job_type": job_type,
            "status": status,
            "position_title": position_title,
            "clinical_specialty": clinical_specialty,
            "clinical_setting": clinical_setting,
            "department_unit": department_unit,
            "description": description,
            "required_credentials": required_credentials,
            "minimum_experience_years": minimum_experience_years,
            "city": city,
            "state": state,
            "country": country,
            "rate_type": rate_type,
            "rate_amount_min": rate_amount_min,
            "rate_amount_max": rate_amount_max,
            "currency": currency,
            "currency_symbol": currency_symbol,
            "facility_location": facility_location,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        # Apply PERMANENT specific fields
        if job_type == JobType.PERMANENT:
            doc["accepts_interns"] = accepts_interns if accepts_interns is not None else False
            doc["rotation_schedule"] = rotation_schedule
            doc["fringe_benefits"] = fringe_benefits or []
        else:
            # For LOCUM jobs, accepts_interns is not applicable
            doc["accepts_interns"] = None
            doc["coverage_start_date"] = coverage_start_date
            doc["coverage_end_date"] = coverage_end_date
            doc["shift_hours"] = shift_hours
            doc["malpractice_insurance_provided"] = malpractice_insurance_provided if malpractice_insurance_provided is not None else False
            doc["travel_housing_reimbursement"] = travel_housing_reimbursement if travel_housing_reimbursement is not None else False
            doc["on_call_requirements"] = on_call_requirements

        return doc
