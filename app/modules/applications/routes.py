from fastapi import logger
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from typing import List, Optional
from bson import ObjectId

from app.core.database import get_database
from app.core.security import get_current_user_id
from app.core.utils import verify_user_status
from app.modules.user import service as user_service
from app.modules.applications import service, schemas
from app.modules.applications.enums import ApplicationStatus
from app.modules.applications.models import ApplicationModel

# Cross-module imports for validation
from app.modules.jobs import service as jobs_service
from app.modules.jobs.enums import JobType, JobStatus

router = APIRouter()

@router.post(
    "", 
    response_model=schemas.ApplicationResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Apply for a job listing"
)
async def apply_to_job(
    payload: schemas.ApplicationCreate,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Submits an application for a unified job listing.
    - **Applicant Requirements**: Only verified **professionals** are allowed to apply.
    - **Validations**: Checks job existence, status (must be OPEN), and blocks duplicate submittals.
    """
    # 1. Verify candidate is active, verified, and role is professional
    user = await verify_user_status(db, user_id, allowed_roles=["professional"])
    if user.get("banned_from_applying"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is banned from applying for jobs."
        )

    # 2. Check if the job exists and is open
    job = await jobs_service.get_job_listing_by_id(db, payload.vacancy_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Targeted job listing not found.")
    if job.get("status") != JobStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"This job listing is no longer accepting applications (status: {job.get('status')})."
        )

    # 3. Prevent duplicate applications
    already_applied = await service.has_user_applied(db, user_id, payload.vacancy_id)
    if already_applied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="You have already submitted an application for this job listing."
        )

    # 4. Create the application
    app_dict = ApplicationModel.new_application(
        candidate_id=user_id,
        vacancy_id=payload.vacancy_id,
        vacancy_type=job.get("job_type"),
        curriculum_vitae_url=payload.curriculum_vitae_url,
        clinical_summary=payload.clinical_summary,
        credentialing_packet_urls=payload.credentialing_packet_urls,
    )

    return await service.create_application(db, user_id, app_dict)

@router.get(
    "", 
    response_model=List[schemas.ApplicationResponse],
    summary="Query applications"
)
async def list_applications(
    candidate_id: Optional[str] = Query(None, description="Filter by candidate ID"),
    vacancy_id: Optional[str] = Query(None, description="Filter by job ID"),
    vacancy_type: Optional[JobType] = Query(None, description="Filter by PERMANENT or LOCUM"),
    is_shortlisted: Optional[bool] = Query(None, description="Filter by shortlist status"),
    is_accepted: Optional[bool] = Query(None, description="Filter by acceptance status"),
    application_status: Optional[ApplicationStatus] = Query(None, description="Filter by application pipeline status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Queries applications submitted across job listings.
    - **Access Controls**:
      - **Professionals** can only view *their own* applications.
      - **Institutes** can only view applications for job listings *they posted*.
      - **Administrators** can view all.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    role = user.get("role")
    
    # Enforce boundaries for non-admin users (Institutes and Professionals)
    if role != "admin":
        if vacancy_id:
            if not ObjectId.is_valid(vacancy_id):
                return []
            job = await jobs_service.get_job_listing_by_id(db, vacancy_id)
            if not job:
                return []
            posted_by_id = job["posted_by"].get("_id") if isinstance(job["posted_by"], dict) else job["posted_by"]
            if posted_by_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are only authorized to query applications for job listings you published."
                )
        else:
            # Find all job listings posted by this user (institute or professional), then filter by those IDs.
            jobs = await db["job_listings"].find({"posted_by": ObjectId(user_id)}).to_list(length=1000)
            allowed_ids = [ObjectId(j["_id"]) for j in jobs]
            if not allowed_ids:
                return []
            
            query_filter: dict = {}
            if is_shortlisted is not None:
                query_filter["is_shortlisted"] = is_shortlisted
            if is_accepted is not None:
                query_filter["is_accepted"] = is_accepted
            if application_status is not None:
                query_filter["application_status"] = application_status
            if vacancy_type is not None:
                query_filter["vacancy_type"] = vacancy_type
                
            query_filter["vacancy_id"] = {"$in": allowed_ids}
            if candidate_id:
                if not ObjectId.is_valid(candidate_id):
                    return []
                query_filter["candidate_id"] = ObjectId(candidate_id)
            
            skip = (page - 1) * limit
            cursor = db["applications"].find(query_filter).sort("created_at", -1).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [await service.populate_application_vacancy(db, d) for d in docs]

    return await service.get_applications(
        db=db,
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        vacancy_type=vacancy_type,
        is_shortlisted=is_shortlisted,
        is_accepted=is_accepted,
        application_status=application_status,
        page=page,
        limit=limit
    )

@router.get(
    "/my-applications", 
    response_model=List[schemas.ApplicationResponse],
    summary="Query applications submitted by the current user"
)
async def list_my_applications(
    vacancy_id: Optional[str] = Query(None, description="Filter by job ID"),
    vacancy_type: Optional[JobType] = Query(None, description="Filter by PERMANENT or LOCUM"),
    is_shortlisted: Optional[bool] = Query(None, description="Filter by shortlist status"),
    is_accepted: Optional[bool] = Query(None, description="Filter by acceptance status"),
    application_status: Optional[ApplicationStatus] = Query(None, description="Filter by application pipeline status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Retrieves all applications submitted by the currently logged-in professional candidate.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    if user.get("role") != "professional" and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only candidates with the professional role or administrators can view application logs."
        )

    return await service.get_applications(
        db=db,
        candidate_id=user_id,
        vacancy_id=vacancy_id,
        vacancy_type=vacancy_type,
        is_shortlisted=is_shortlisted,
        is_accepted=is_accepted,
        application_status=application_status,
        page=page,
        limit=limit
    )

@router.get(
    "/check-applied", 
    response_model=dict,
    summary="Check if user has already applied for a job listing"
)
async def check_user_has_applied(
    vacancy_id: str = Query(..., description="The ID of the vacancy/job listing"),
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Returns whether the currently authenticated professional user has already applied for a specific job listing,
    and returns the details of the application if it exists.
    """
    application = await service.get_user_application_for_vacancy(db, user_id, vacancy_id)
    if application:
        return {"applied": True, "application": application}
    return {"applied": False, "application": None}

@router.get(
    "/{application_id}", 
    response_model=schemas.ApplicationResponse,
    summary="Get application details"
)
async def read_application(
    application_id: str,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Retrieves details of a specific application.
    - **Permissions**: Accessible by the applicant, the facility host who posted the job listing, or administrators.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    application = await service.get_application_by_id(db, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application record not found.")

    role = user.get("role")
    candidate_id = application.get("candidate_id")
    if isinstance(candidate_id, ObjectId):
        candidate_id = str(candidate_id)

    posted_by = None
    vacancy_info = application.get("vacancy_id")
    if isinstance(vacancy_info, dict):
        posted_by = vacancy_info.get("posted_by")
    else:
        vac = await jobs_service.get_job_listing_by_id(db, str(vacancy_info))
        if vac:
            posted_by = vac.get("posted_by")
    if isinstance(posted_by, dict):
        posted_by = posted_by.get("_id")
    if isinstance(posted_by, ObjectId):
        posted_by = str(posted_by)

    # Allow access if the user is the candidate, the job owner (posting facility/user), or an admin
    is_owner = (str(posted_by) == user_id)
    is_candidate = (str(candidate_id) == user_id)
    is_admin = (role == "admin")

    if not (is_owner or is_candidate or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return application

@router.put(
    "/{application_id}/shortlist", 
    response_model=schemas.ApplicationResponse,
    summary="Shortlist an applicant"
)
async def shortlist_application(
    application_id: str,
    payload: schemas.ApplicationShortlistUpdate,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Shortlists or removes an applicant from the shortlist pipeline.
    - **Pipeline Transitions**: Shortlisting sets the status to **Credentialing Review**. Un-shortlisting reverts to **Submitted**.
    - **Permissions**: Only the job/shift owner or an administrator can update.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    app = await service.get_application_by_id(db, application_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    # Ownership check
    posted_by = None
    vacancy_info = app["vacancy_id"]
    if isinstance(vacancy_info, dict):
        posted_by = vacancy_info.get("posted_by")
    else:
        vac = await jobs_service.get_job_listing_by_id(db, str(vacancy_info))
        if vac:
            posted_by = vac["posted_by"]
            if isinstance(posted_by, dict):
                posted_by = posted_by.get("_id")

    if not posted_by:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Targeted job listing no longer exists.")

    # log the posted_by id and user id for debugging
    print(f"Posted by: {posted_by.get('_id')}, User ID: {user_id}")
    
    if str(posted_by.get('_id')) != str(user_id) and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the posting facility or an administrator can shortlist candidates."
        )

    updated = await service.update_application_shortlist(db, application_id, payload.is_shortlisted)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed.")
    return updated

@router.put(
    "/{application_id}/accept", 
    response_model=schemas.ApplicationResponse,
    summary="Accept an applicant"
)
async def accept_application(
    application_id: str,
    payload: schemas.ApplicationAcceptUpdate,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Accepts/contracts an applicant for a job.
    - **Pipeline Transitions**: Accepting a candidate sets `is_shortlisted` to `True` and moves the application status to **Accepted**. Reverting returns it to **Credentialing Review** or **Submitted**.
    - **Permissions**: Only the job/shift owner or an administrator can update.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    app = await service.get_application_by_id(db, application_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    # Ownership check
    posted_by = None
    vacancy_info = app["vacancy_id"]
    if isinstance(vacancy_info, dict):
        posted_by = vacancy_info.get("posted_by")
    else:
        vac = await jobs_service.get_job_listing_by_id(db, str(vacancy_info))
        if vac:
            posted_by = vac["posted_by"]
            if isinstance(posted_by, dict):
                posted_by = posted_by.get("_id")

    if not posted_by:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Targeted job listing no longer exists.")

    # log the posted_by id and user id for debugging
    print(f"Posted by: {posted_by.get('_id')}, User ID: {user_id}")
    if str(posted_by.get('_id')) != str(user_id) and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the posting facility or an administrator can accept candidates."
        )

    updated = await service.update_application_acceptance(db, application_id, payload.is_accepted)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed.")
    return updated

@router.put(
    "/{application_id}/status", 
    response_model=schemas.ApplicationResponse,
    summary="Update application status directly"
)
async def update_status_directly(
    application_id: str,
    application_status: ApplicationStatus = Body(..., embed=True, description="Target status"),
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Updates the raw application pipeline status directly (e.g. declining an application).
    - **Permissions**: Only the job owner or an administrator can update.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    app = await service.get_application_by_id(db, application_id)
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    # Ownership check
    posted_by = None
    vacancy_info = app["vacancy_id"]
    if isinstance(vacancy_info, dict):
        posted_by = vacancy_info.get("posted_by")
    else:
        vac = await jobs_service.get_job_listing_by_id(db, str(vacancy_info))
        if vac:
            posted_by = vac["posted_by"]
            if isinstance(posted_by, dict):
                posted_by = posted_by.get("_id")

    if not posted_by:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Targeted job listing no longer exists.")

    # log the posted_by id and user id for debugging
    print(f"Posted by: {posted_by.get('_id')}, User ID: {user_id}")

    if str(posted_by.get('_id')) != str(user_id) and user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the posting facility or an administrator can update application statuses."
        )

    updated = await service.update_application_status(db, application_id, application_status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Operation failed.")
    return updated
