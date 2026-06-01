from pydantic import BaseModel, Field
from app.modules.jobs.enums import JobType

class ReassignJobPayload(BaseModel):
    new_owner_id: str = Field(..., description="MongoDB ObjectId of the new owner")
    job_type: JobType = Field(..., description="Type of job (PERMANENT or LOCUM)")
