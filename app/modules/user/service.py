from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from typing import Any
import secrets

async def generate_unique_referral_code(db: AsyncIOMotorDatabase) -> str:
    while True:
        # Generate an 8-character uppercase hex string as the referral code
        code = secrets.token_hex(4).upper()
        # Check if this code already exists in the database
        exists = await db["users"].find_one({"referral_code": code})
        if not exists:
            return code

async def get_user_by_email(db: AsyncIOMotorDatabase, email: str):
    return await db["users"].find_one({"email": email})

async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str):
    if not ObjectId.is_valid(user_id):
        return None
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
        
        # Convert referred_by to string if stored as ObjectId
        if "referred_by" in user and user["referred_by"]:
            user["referred_by"] = str(user["referred_by"])
            
        # Dynamic backfill of referral code for backward compatibility
        if "referral_code" not in user or not user["referral_code"]:
            referral_code = await generate_unique_referral_code(db)
            await db["users"].update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"referral_code": referral_code}}
            )
            user["referral_code"] = referral_code
    return user

async def create_user(db: AsyncIOMotorDatabase, user_data: dict) -> dict:
    result = await db["users"].insert_one(user_data)
    created_user = await db["users"].find_one({"_id": result.inserted_id})
    if not created_user:
        raise RuntimeError("Failed to retrieve user after insert")
    created_user["_id"] = str(created_user["_id"])
    return created_user

async def update_credit_balance(db: AsyncIOMotorDatabase, user_id: str, amount: int, operation: str):
    if not ObjectId.is_valid(user_id):
        return None
        
    increment = amount if operation == "add" else -amount
    query: dict[str, Any] = {"_id": ObjectId(user_id)}
    
    # If subtracting, ensure balance is sufficient
    if operation != "add":
        query["credit_balance"] = {"$gte": amount}

    result = await db["users"].update_one(
        query, 
        {
            "$inc": {"credit_balance": increment},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )
    
    # If no document was modified, it means either user not found OR insufficient balance
    if result.modified_count == 0:
        return None

    # Return new balance
    updated_user = await get_user_by_id(db, user_id)
    return updated_user["credit_balance"] if updated_user else None

async def update_user_profile(db: AsyncIOMotorDatabase, user_id: str, update_data: dict):
    if not ObjectId.is_valid(user_id):
        return None
    
    # Filter out None values to only update provided fields
    update_fields = {k: v for k, v in update_data.items() if v is not None}
    
    if not update_fields:
        return None  # No fields to update

    # Fetch existing user to check and resolve employment status
    existing_user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not existing_user:
        return None

    emp_status = update_fields.get("employment_status", existing_user.get("employment_status"))
    if emp_status in [None, "unemployed"]:
        # Force current workplace to None if unemployed or status is not set
        update_fields["current_workplace"] = None
    elif "current_workplace" in update_fields and not update_fields["current_workplace"]:
        # Standardize empty/falsy workplace to None
        update_fields["current_workplace"] = None
    
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    result = await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields}
    )
    
    if result.matched_count == 0:
        return None
    
    # Return updated user
    return await get_user_by_id(db, user_id)

async def delete_user(db: AsyncIOMotorDatabase, user_id: str):
    if not ObjectId.is_valid(user_id):
        return False
    
    # Soft Delete: Mark inactive/deleted and reset credits to 2
    result = await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "is_active": False,
            "is_deleted": True,
            "credit_balance": 2,
            "updated_at": datetime.now(timezone.utc),
        }}
    )

    # Clean up credit transactions
    await db["credit_transactions"].delete_many({"user_id": ObjectId(user_id)})
     
    # Return True if user exists (matched), regardless of if modified (might already be inactive)
    return result.matched_count > 0

async def apply_referral_code(db: AsyncIOMotorDatabase, user_id: str, referral_code: str):
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
    #     source=CreditSource.BONUS,
    #     description="Referral Signup Bonus"
    # )
    
    return {"message": "Referral code applied successfully", "referrer_name": referrer.get("full_name")}