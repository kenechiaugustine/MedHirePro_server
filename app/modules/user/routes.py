from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List
from bson import ObjectId
from app.core.database import get_database
from app.core.security import get_current_user_id
from app.modules.user import service, schemas
from app.modules.credits.enums import CreditSource, CreditType

router = APIRouter()

@router.get("/me", response_model=schemas.UserResponse)
async def read_user_me(
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/update-credit", deprecated=True)
async def update_credit(
    payload: schemas.UserUpdateCredits,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    new_balance = await service.update_credit_balance(db, user_id, payload.amount, payload.operation)
    if new_balance is None:
        raise HTTPException(status_code=400, detail="Operation failed or insufficient funds")
    
    return {"message": "Credits updated", "new_balance": new_balance}

@router.put("/update-profile", response_model=schemas.UserResponse)
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
    
    return updated_user

@router.delete("/me", status_code=204)
async def delete_user_me(
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    success = await service.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found or already deleted")
    return

@router.get("/referral-details", response_model=schemas.UserReferralDetailsResponse)
async def get_referral_details(
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    user = await service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Query all referral credit earnings for this user
    cursor = db["credit_transactions"].find({
        "user_id": ObjectId(user_id),
        "source": CreditSource.REFERRAL,
        "type": CreditType.EARN
    })
    transactions = await cursor.to_list(length=None)
    total_earned = sum(t["amount"] for t in transactions)
    
    return {
        "referral_code": user.get("referral_code"),
        "referred_count": user.get("referred_count", 0),
        "referred_by": user.get("referred_by"),
        "total_referral_credits_earned": total_earned
    }

@router.get("/referred-users", response_model=List[schemas.UserResponse])
async def get_referred_users(
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    # Retrieve all users referred by this user
    cursor = db["users"].find({"referred_by": ObjectId(user_id)})
    referred_users = await cursor.to_list(length=None)
    
    # Format the users properly
    for u in referred_users:
        u["_id"] = str(u["_id"])
        if "referred_by" in u and u["referred_by"]:
            u["referred_by"] = str(u["referred_by"])
            
    return referred_users

@router.post("/apply-referral")
async def apply_referral(
    payload: schemas.ApplyReferralRequest,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    return await service.apply_referral_code(db, user_id, payload.referral_code)