from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from bson import ObjectId
from app.core.database import get_database
from app.core.security import get_current_user_id, get_current_admin
from app.core.response import PaginatedResponse, SingleResponse, create_paginated_response, create_single_response
from app.modules.reviews import service, schemas
from app.modules.reviews.models import ReviewModel
from app.modules.user import service as user_service

router = APIRouter()

@router.post(
    "", 
    response_model=SingleResponse[schemas.ReviewResponse], 
    status_code=status.HTTP_201_CREATED,
    summary="Submit platform review/feedback"
)
async def submit_review(
    payload: schemas.ReviewCreate,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Submits a new review/feedback for the platform.
    Accessible by both professionals and institutes.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalid or user inactive."
        )

    review_dict = ReviewModel.new_review(
        user_id=user_id,
        rating=payload.rating,
        comment=payload.comment
    )

    created = await service.create_review(db, review_dict)
    
    # Attach user details to response
    created["user_details"] = user
    return create_single_response(created)

@router.get(
    "", 
    response_model=PaginatedResponse[schemas.ReviewResponse],
    summary="Retrieve reviews (Admin only)"
)
async def list_reviews(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50000),
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_database)
):
    """
    Retrieves all reviews/feedback submitted by platform users.
    Only accessible by administrators.
    """
    reviews, total_count = await service.get_all_reviews(db, page=page, limit=limit)
    return create_paginated_response(reviews, page, limit, total_count)

@router.put(
    "/{review_id}/visibility",
    response_model=SingleResponse[schemas.ReviewResponse],
    summary="Update review visibility (Admin only)"
)
async def update_review_visibility(
    review_id: str,
    is_public: bool = Query(..., description="Set to True for public, False for private"),
    current_admin: dict = Depends(get_current_admin),
    db = Depends(get_database)
):
    """
    Updates the visibility of a review, marking it as public or private.
    Only accessible by administrators.
    """
    if not ObjectId.is_valid(review_id):
        raise HTTPException(status_code=400, detail="Invalid review ID format")

    updated = await service.update_review_visibility(db, review_id, is_public)
    if not updated:
        raise HTTPException(status_code=404, detail="Review not found")
        
    return create_single_response(updated)
