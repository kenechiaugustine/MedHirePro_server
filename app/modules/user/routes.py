from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.database import get_database
from app.core.security import get_current_user_id
from app.core.response import SingleResponse, create_single_response
from app.modules.user import service, schemas

router = APIRouter()

@router.get("/me", response_model=SingleResponse[schemas.UserResponse])
async def read_user_me(
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return create_single_response(user)

@router.put("/update-credit", deprecated=True, response_model=SingleResponse[dict])
async def update_credit(
    payload: schemas.UserUpdateCredits,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    new_balance = await service.update_credit_balance(db, user_id, payload.amount, payload.operation)
    if new_balance is None:
        raise HTTPException(status_code=400, detail="Operation failed or insufficient funds")
    
    return create_single_response({"message": "Credits updated", "new_balance": new_balance})

@router.put("/update-profile", response_model=SingleResponse[schemas.UserResponse])
async def update_profile(
    payload: schemas.UserUpdateProfile,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    updated_user = await service.update_user_profile(
        db, 
        user_id, 
        payload.model_dump(exclude_unset=False)
    )
    if not updated_user:
        raise HTTPException(status_code=400, detail="Failed to update profile")
    
    return create_single_response(updated_user)

@router.delete("/me", status_code=204)
async def delete_user_me(
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    success = await service.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or already deleted")
    return