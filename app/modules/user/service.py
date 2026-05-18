from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from typing import Any

async def get_user_by_email(db: AsyncIOMotorDatabase, email: str):
    return await db["users"].find_one({"email": email})

async def get_user_by_id(db: AsyncIOMotorDatabase, user_id: str):
    if not ObjectId.is_valid(user_id):
        return None
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
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
    
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    result = await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
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