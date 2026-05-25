from fastapi import APIRouter, Depends, HTTPException
from typing import List
from bson import ObjectId
from app.core.database import get_database
from app.core.security import get_current_user_id
from app.modules.user import schemas as user_schemas
from app.modules.user import service as user_service
from app.modules.referral import schemas, service
from app.modules.credits.enums import CreditSource, CreditType

router = APIRouter()

@router.post("/apply")
async def apply_referral(
    payload: schemas.ApplyReferralRequest,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    return await service.apply_referral_code(db, user_id, payload.referral_code)

@router.get("/details", response_model=schemas.UserReferralDetailsResponse)
async def get_referral_details(
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    user = await user_service.get_user_by_id(db, user_id)
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

@router.get("/users", response_model=List[user_schemas.UserResponse])
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
