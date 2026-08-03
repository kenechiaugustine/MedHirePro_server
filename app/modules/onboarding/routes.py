from fastapi import APIRouter, Depends, HTTPException, Body, status, Query
from pydantic import ValidationError
from app.core.database import get_database
from app.core.security import get_current_user_id, get_current_admin
from app.core.response import PaginatedResponse, SingleResponse, create_paginated_response, create_single_response
from app.modules.user import service as user_service
from app.modules.onboarding import service, schemas

router = APIRouter()


@router.post("/submit", status_code=status.HTTP_200_OK, response_model=SingleResponse[dict])
async def submit_onboarding_form(
    payload: dict = Body(..., example={
        "is_intern": False,
        "licence_number": "MD-123456",
        "licence_expiry": "2029-12-31",
        "licence_document_url": "https://res.cloudinary.com/demo/image/upload/v1/licence.png",
        "degree_document_url": "https://res.cloudinary.com/demo/image/upload/v1/degree.png",
        "id_document_url": "https://res.cloudinary.com/demo/image/upload/v1/passport.png",
        "specialty": "Cardiology",
        "employment_status": "unemployed",
        "current_workplace": ""
    }),
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Submits onboarding credentials using media URLs returned by the media module.
    Dynamic validation checks:
    - If user role is professional, conditional validation ensures interns submit placement letters and licensed practitioners submit license files.
    - If user role is institute, corporate EIN, operating license, address and representative IDs are validated.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    role = user.get("role")
    validated_details = {}
    
    # Perform dynamic schema validation based on user role
    try:
        if role == "professional":
            # Validates as Professional
            validated_data = schemas.ProfessionalOnboardingSubmit.model_validate(payload)
            validated_details = validated_data.model_dump()
        elif role == "institute":
            # Validates as Institute
            validated_data = schemas.InstituteOnboardingSubmit.model_validate(payload)
            validated_details = validated_data.model_dump()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators do not require onboarding"
            )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )
        
    submission = await service.submit_onboarding(db, user_id, role, validated_details)
    return create_single_response({
        "message": "Onboarding credentials submitted successfully for review",
        "submission": submission
    })


@router.get("/status", response_model=SingleResponse[dict])
async def get_my_onboarding_status(
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Retrieves the current onboarding status and latest submission of the logged-in user.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    submission = await service.get_onboarding_status(db, user_id)
    return create_single_response({
        "onboarding_status": user.get("onboarding_status", "not_started"),
        "is_verified": user.get("is_verified", False),
        "submission": submission
    })


@router.get("/admin/pending", response_model=PaginatedResponse[dict])
async def get_pending_onboardings(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50000, description="Items per page"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    admin = Depends(get_current_admin),
    db = Depends(get_database)
):
    """
    Admin-only endpoint to list onboarding submissions that are currently pending verification.
    Submissions are sorted in FIFO order.
    """
    effective_skip = skip if skip > 0 else (page - 1) * limit
    submissions, total_count = await service.list_pending_submissions(db, effective_skip, limit)
    return create_paginated_response(submissions, page, limit, total_count)


@router.post("/admin/review", response_model=SingleResponse[dict])
async def review_onboarding_submission(
    payload: schemas.AdminReviewPayload,
    admin = Depends(get_current_admin),
    db = Depends(get_database)
):
    """
    Admin-only endpoint to approve or reject an onboarding submission.
    Upon approval, user profile details are synchronized and the account is marked is_verified=True.
    Upon rejection, a rejection reason is recorded.
    """
    admin_id = str(admin["_id"])
    submission = await service.review_onboarding(
        db,
        payload.submission_id,
        admin_id,
        payload.action,
        payload.rejection_reason
    )
    return create_single_response({
        "message": f"Onboarding submission has been successfully {payload.action}ed",
        "submission": submission
    })
