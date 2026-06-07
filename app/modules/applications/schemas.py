from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime
from app.modules.jobs.enums import JobType
from app.modules.jobs.schemas import JobListingResponse
from app.modules.applications.enums import ApplicationStatus

class ApplicationCreate(BaseModel):
    vacancy_id: str = Field(..., description="MongoDB ObjectId of the targeted unified job listing")
    curriculum_vitae_url: str = Field(..., description="Secure Cloudinary / Media URL of the candidate's CV")
    clinical_summary: str = Field(..., min_length=10, description="Cover letter / professional summary explaining clinical capabilities")
    credentialing_packet_urls: Optional[List[str]] = Field(default_factory=list, description="Other supporting documents (licenses, certificates)")

class ApplicationShortlistUpdate(BaseModel):
    is_shortlisted: bool

class ApplicationAcceptUpdate(BaseModel):
    is_accepted: bool

class CandidateDetails(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    specialty: Optional[str] = None
    avatar_url: Optional[str] = None

class ApplicationResponse(BaseModel):
    id: str = Field(alias="_id")
    candidate_id: str
    candidate_details: Optional[CandidateDetails] = None
    vacancy_id: Union[JobListingResponse, str]
    vacancy_type: JobType
    curriculum_vitae_url: str
    clinical_summary: str
    credentialing_packet_urls: List[str]
    is_shortlisted: bool
    is_accepted: bool
    application_status: ApplicationStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
