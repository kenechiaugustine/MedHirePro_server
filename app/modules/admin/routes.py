from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date
from bson import ObjectId

from app.core.database import get_database
from app.core.security import get_current_admin
from app.modules.user import schemas as user_schemas
from app.modules.user.enums import UserRole
from app.modules.credits import schemas as credits_schemas
from app.modules.credits import enums as credits_enums
from app.modules.admin import service

router = APIRouter()

@router.get("/users", response_model=List[user_schemas.UserResponse])
async def read_all_users(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name, email, or facility"),
    db = Depends(get_database),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Fetch all users with optional filtering, search, and pagination.
    Only accessible by administrators.
    """
    return await service.get_all_users(
        db=db,
        page=page,
        limit=limit,
        role=role,
        is_active=is_active,
        search=search
    )

@router.get("/users/{user_id}/credits", response_model=List[credits_schemas.CreditTransactionResponse])
async def read_user_credits_history(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    type: Optional[credits_enums.CreditType] = Query(None, description="Filter by transaction type (earn/spend)"),
    source: Optional[credits_enums.CreditSource] = Query(None, description="Filter by credit source"),
    db = Depends(get_database),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Fetch the credit transaction history for a specific user.
    Only accessible by administrators.
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
        
    date_str = str(date) if date else None
    
    return await service.get_user_credits_history(
        db=db,
        user_id=user_id,
        page=page,
        limit=limit,
        date_filter=date_str,
        type=type,
        source=source
    )

@router.get("/users/{user_id}/referrals", response_model=List[user_schemas.UserResponse])
async def read_user_referrals(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    db = Depends(get_database),
    current_admin: dict = Depends(get_current_admin)
):
    """
    Fetch the list of users referred by a specific user.
    Only accessible by administrators.
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID format")
        
    return await service.get_user_referrals(
        db=db,
        user_id=user_id,
        page=page,
        limit=limit
    )
