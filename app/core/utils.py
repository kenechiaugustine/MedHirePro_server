from typing import List, Optional
from fastapi import HTTPException, status
from app.modules.user import service as user_service

async def verify_user_status(db, user_id: str, allowed_roles: Optional[List[str]] = None) -> dict:
    """
    Validates that a user exists, is active, is verified, and possesses one of the allowed roles.
    Administrators bypass verification constraints.
    Centralized in app/core/utils.py for global reusability.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User profile not found."
        )
    if not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated."
        )
    
    # Admin role bypasses verification constraints
    is_admin = user.get("role") == "admin"
    if not is_admin and not user.get("is_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your profile is not verified. You must complete professional/facility onboarding and be approved first."
        )
    if allowed_roles and user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action is restricted to: {', '.join(allowed_roles)}. Your role is: {user.get('role')}."
        )
    return user
