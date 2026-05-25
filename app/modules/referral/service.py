import secrets
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

async def generate_unique_referral_code(db: AsyncIOMotorDatabase) -> str:
    while True:
        # Generate an 8-character uppercase hex string as the referral code
        code = secrets.token_hex(4).upper()
        # Check if this code already exists in the database
        exists = await db["users"].find_one({"referral_code": code})
        if not exists:
            return code

async def apply_referral_code(db: AsyncIOMotorDatabase, user_id: str, referral_code: str):
    # Dynamic imports to resolve circular dependency at startup
    from app.modules.user import service as user_service
    from app.modules.credits import service as credits_service
    from app.modules.credits.enums import CreditType, CreditSource
    from fastapi import HTTPException
           
    REFERRAL_AWARD = 5  # Credits awarded to referrer
    # REFERRAL_BONUS = 2    # Credits awarded to referred user
    
    
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID.")
        
    # 1. Fetch user applying the code
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    # 2. Check if they already have a referrer
    if user.get("referred_by"):
        raise HTTPException(status_code=400, detail="Referral code already applied for this user.")
        
    # 3. Find referrer by code
    referrer = await db["users"].find_one({"referral_code": referral_code})
    if not referrer:
        raise HTTPException(status_code=400, detail="Invalid referral code.")
        
    referrer_id = referrer["_id"]
    
    # 4. Check self-referral
    if referrer_id == user["_id"]:
        raise HTTPException(status_code=400, detail="You cannot refer yourself.")
        
    # 5. Save the relationship
    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {"referred_by": referrer_id}}
    )
    
    # 6. Increment referrer's count
    await db["users"].update_one(
        {"_id": referrer_id},
        {"$inc": {"referred_count": 1}}
    )
    
    # 7. Reward referrer
    await credits_service.process_transaction(
        db=db,
        user_id=str(referrer_id),
        amount=REFERRAL_AWARD,
        type=CreditType.EARN,
        source=CreditSource.REFERRAL,
        description=f"Referral Bonus - referred {user['email']}"
    )
    
    # 8. Reward referred user
    # await credits_service.process_transaction(
    #     db=db,
    #     user_id=str(user["_id"]),
    #     amount=REFERRAL_BONUS,
    #     type=CreditType.EARN,
    #     source=CreditSource.REFERRAL,
    #     description="Referral Signup Bonus"
    # )
    
    return {"message": "Referral code applied successfully", "referrer_name": referrer.get("full_name")}
