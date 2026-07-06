from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from bson import ObjectId

from app.core.database import get_database
from app.core.security import get_current_user_id, get_current_user_id_optional
from app.core.utils import verify_user_status
from app.modules.user import service as user_service
from app.modules.jobs import service, schemas
from app.modules.jobs.enums import (
    JobType,
    JobStatus,
    RateType,
    ClinicalSetting,
    ClinicalSpecialty,
)
from app.modules.jobs.models import JobListingModel

router = APIRouter()

@router.post(
    "/permanent", 
    response_model=schemas.JobListingResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Post a permanent job listing"
)
async def post_permanent_job(
    payload: schemas.PermanentJobListingCreate,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Creates a new permanent job listing.
    - **Host Requirements**: Only verified **institutes** or **administrators** can post permanent jobs.
    - **Administrators**: Bypasses the verification requirement.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    role = user.get("role")
    
    # 1. Enforce verified Institute or Admin
    await verify_user_status(db, user_id, allowed_roles=["institute", "admin"])

    # 2. Instantiate the model document
    job_dict = JobListingModel.new_job_listing(
        posted_by=user_id,
        poster_type=role,
        job_type=JobType.PERMANENT,
        position_title=payload.position_title,
        clinical_specialty=payload.clinical_specialty,
        clinical_setting=payload.clinical_setting,
        department_unit=payload.department_unit,
        description=payload.description,
        required_credentials=payload.required_credentials,
        minimum_experience_years=payload.minimum_experience_years,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        rate_type=payload.rate_type,
        rate_amount_min=payload.rate_amount_min,
        rate_amount_max=payload.rate_amount_max,
        currency=payload.currency,
        currency_symbol=payload.currency_symbol,
        accepts_interns=payload.accepts_interns,
        facility_location=payload.facility_location,
        rotation_schedule=payload.rotation_schedule,
        fringe_benefits=payload.fringe_benefits,
    )
    
    return await service.create_job_listing(db, user_id, job_dict)

@router.post(
    "/locum", 
    response_model=schemas.JobListingResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Post a locum shift vacancy"
)
async def post_locum_job(
    payload: schemas.LocumJobListingCreate,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Creates a new locum shift vacancy.
    - **Host Requirements**: Open to any verified user (**institutes**, **professionals**, or **administrators**).
    - **Administrators**: Bypasses the verification requirement.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    role = user.get("role")
    
    # 1. Enforce verified Institute, Professional, or Admin
    await verify_user_status(db, user_id, allowed_roles=["institute", "professional", "admin"])

    # 2. Instantiate the model document
    job_dict = JobListingModel.new_job_listing(
        posted_by=user_id,
        poster_type=role,
        job_type=JobType.LOCUM,
        position_title=payload.position_title,
        clinical_specialty=payload.clinical_specialty,
        clinical_setting=payload.clinical_setting,
        department_unit=payload.department_unit,
        description=payload.description,
        required_credentials=payload.required_credentials,
        minimum_experience_years=payload.minimum_experience_years,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        rate_type=payload.rate_type,
        rate_amount_min=payload.rate_amount_min,
        rate_amount_max=payload.rate_amount_max,
        currency=payload.currency,
        currency_symbol=payload.currency_symbol,
        facility_location=payload.facility_location,
        
        # Locum specific parameters
        coverage_start_date=payload.coverage_start_date,
        coverage_end_date=payload.coverage_end_date,
        shift_hours=payload.shift_hours,
        malpractice_insurance_provided=payload.malpractice_insurance_provided,
        travel_housing_reimbursement=payload.travel_housing_reimbursement,
        on_call_requirements=payload.on_call_requirements,
    )
    
    return await service.create_job_listing(db, user_id, job_dict)

@router.get(
    "", 
    response_model=List[schemas.JobListingResponse],
    summary="Query job listings"
)
async def list_job_listings(
    job_type: Optional[JobType] = Query(None, description="Filter by PERMANENT or LOCUM"),
    clinical_specialty: Optional[ClinicalSpecialty] = Query(None, description="Filter by medical specialty"),
    clinical_setting: Optional[ClinicalSetting] = Query(None, description="Filter by physical clinical setting"),
    status: Optional[JobStatus] = Query(None, description="Filter by job status (defaults to OPEN for public/others)"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user_id: Optional[str] = Depends(get_current_user_id_optional),
    db = Depends(get_database)
):
    """
    Retrieves all available job listings matching dynamic filter criteria.
    """
    is_admin = False
    if current_user_id:
        user = await user_service.get_user_by_id(db, current_user_id)
        if user and user.get("role") == "admin":
            is_admin = True

    if not is_admin:
        if status == JobStatus.FLAGGED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view flagged listings."
            )
        exclude_flagged = True
        if status is None:
            status = JobStatus.OPEN
    else:
        exclude_flagged = False

    return await service.get_job_listings(
        db=db,
        job_type=job_type,
        clinical_specialty=clinical_specialty,
        clinical_setting=clinical_setting,
        status=status,
        page=page,
        limit=limit,
        exclude_flagged=exclude_flagged
    )

@router.get(
    "/my-listings", 
    response_model=List[schemas.JobListingResponse],
    summary="Query job listings posted by the current user"
)
async def list_my_job_listings(
    job_type: Optional[JobType] = Query(None, description="Filter by PERMANENT or LOCUM"),
    clinical_specialty: Optional[ClinicalSpecialty] = Query(None, description="Filter by medical specialty"),
    clinical_setting: Optional[ClinicalSetting] = Query(None, description="Filter by physical clinical setting"),
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Retrieves all job listings posted by the currently authenticated user.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    listings = await service.get_job_listings_with_applicant_counts(
        db=db,
        posted_by=user_id,
        job_type=job_type,
        clinical_specialty=clinical_specialty,
        clinical_setting=clinical_setting,
        status=status,
        page=page,
        limit=limit
    )

    return listings

@router.get(
    "/{job_id}", 
    response_model=schemas.JobListingResponse,
    summary="Get job listing details"
)
async def read_job_listing(
    job_id: str,
    current_user_id: Optional[str] = Depends(get_current_user_id_optional),
    db = Depends(get_database)
):
    """
    Retrieves details of a specific job listing by ID.
    """
    job = await service.get_job_listing_by_id(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Job listing not found"
        )
        
    if job.get("status") == JobStatus.FLAGGED:
        is_authorized = False
        if current_user_id:
            user = await user_service.get_user_by_id(db, current_user_id)
            if user:
                role = user.get("role")
                posted_by_id = job["posted_by"].get("_id") if isinstance(job["posted_by"], dict) else job["posted_by"]
                if role == "admin" or str(posted_by_id) == current_user_id:
                    is_authorized = True
        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Job listing not found"
            )
            
    return job

@router.put(
    "/{job_id}", 
    response_model=schemas.JobListingResponse,
    summary="Update job listing"
)
async def modify_job_listing(
    job_id: str,
    payload: schemas.JobListingUpdate,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Modifies details of an existing job listing.
    - **Permissions**: Only the original creator or an administrator can update.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session or deactivated user.")

    job = await service.get_job_listing_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    posted_by_id = job["posted_by"].get("_id") if isinstance(job["posted_by"], dict) else job["posted_by"]
    if posted_by_id != user_id and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have authorization to edit this job listing."
        )

    update_dict = payload.model_dump(exclude_unset=True)
    if job.get("status") == JobStatus.FLAGGED and user.get("role") != "admin":
        update_dict["status"] = update_dict.get("status", JobStatus.OPEN)
        update_dict["flagged_reason"] = None
        update_dict["flagged_at"] = None

    updated = await service.update_job_listing(db, job_id, update_dict)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Update failed.")
    return updated

@router.delete(
    "/{job_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete job listing"
)
async def remove_job_listing(
    job_id: str,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Permanently deletes a job listing.
    - **Permissions**: Only the original creator or an administrator can delete.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    job = await service.get_job_listing_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job listing not found.")

    posted_by_id = job["posted_by"].get("_id") if isinstance(job["posted_by"], dict) else job["posted_by"]
    if posted_by_id != user_id and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have authorization to delete this job listing."
        )

    success = await service.delete_job_listing(db, job_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deletion failed.")
    return
