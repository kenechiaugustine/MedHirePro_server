from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from fastapi import HTTPException
from app.modules.credits.models import CreditTransactionModel
from app.modules.credits.enums import CreditType, CreditSource
from app.modules.user import service as user_service

# Get start of today (UTC)
def get_start_of_today_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(year=now.year, month=now.month, day=now.day)

# --- 1. Eligibility Check (Rolling 24h Window) ---
async def check_earning_eligibility(db: AsyncIOMotorDatabase, user_id: str, source: CreditSource, amount_to_earn: int):
    """
    Returns True if user is allowed to earn.
    Raises HTTPException if limit reached.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Define the 24-hour window
    start_of_today = get_start_of_today_utc()

    # A. Logic for Daily source (Count total earned in last 24h)
    if source == CreditSource.DAILY:
        user_cap = user.get("daily_credit_cap", 20) # Fallback to 20 if missing
        
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "source": CreditSource.DAILY,
                    "created_at": {"$gte": start_of_today}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_earned": {"$sum": "$amount"}
                }
            }
        ]
        
        result = await db["credit_transactions"].aggregate(pipeline).to_list(length=1)
        total_earned_today = result[0]["total_earned"] if result else 0
        
        if (total_earned_today + amount_to_earn) > user_cap:
            raise HTTPException(
                status_code=429, 
                detail=f"Daily credit limit reached. You have earned {total_earned_today}/{user_cap} credits today."
            )

    # B. Logic for One-Time-Per-Day Actions (Socials)
    elif source == CreditSource.SOCIALS:
        # Check if ANY transaction exists in the window
        exists = await db["credit_transactions"].find_one({
            "user_id": ObjectId(user_id),
            "source": source,
            "created_at": {"$gte": start_of_today}
        })
        
        if exists:
            raise HTTPException(
                status_code=429, 
                detail=f"{source.value.replace('_', ' ').title()} reward already claimed in the last 24 hours."
            )

    return True

# --- 2. Record Transaction ---
async def process_transaction(
    db: AsyncIOMotorDatabase, 
    user_id: str, 
    amount: int, 
    type: CreditType, 
    source: CreditSource,
    description: Optional[str] = None
):
    # 1. Create Transaction Log
    tx_model = CreditTransactionModel.new_transaction(
        user_id=ObjectId(user_id),
        amount=amount,
        type=type,
        source=source,
        description=description
    )
    
    # 2. Atomically Update User Balance
    if type == CreditType.SPEND:
        # Atomic check-and-update
        result = await db["users"].update_one(
            {"_id": ObjectId(user_id), "credit_balance": {"$gte": amount}},
            {"$inc": {"credit_balance": -amount}}
        )
        
        if result.modified_count == 0:
             raise HTTPException(status_code=400, detail="Insufficient credit balance")
             
    else:
        # For earning, just increment
        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$inc": {"credit_balance": amount}}
        )

    # Insert log only after successful balance update
    await db["credit_transactions"].insert_one(tx_model)

    updated_user = await user_service.get_user_by_id(db, user_id)
    if not updated_user:
        raise RuntimeError("Failed to retrieve user after transaction")

    return {
        "new_balance": updated_user["credit_balance"],
        "message": "Transaction successful"
    }

# --- 3. Get History ---
# --- User Function ---
async def get_user_history(db: AsyncIOMotorDatabase, user_id: str, page: int, limit: int, date_filter: Optional[str] = None, type: Optional[CreditType] = None, source: Optional[CreditSource] = None):
    skip = (page - 1) * limit
    query: dict[str, Any] = {"user_id": ObjectId(user_id)}

    # add filter by type and source
    if type:
        query["type"] = type
    if source:
        query["source"] = source

    # Apply Date Filter
    if date_filter:
        try:
            # Parse 'YYYY-MM-DD'
            start_date = datetime.strptime(date_filter, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)
            query["created_at"] = {"$gte": start_date, "$lt": end_date}
        except ValueError:
            pass # Ignore invalid date formats

    cursor = db["credit_transactions"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    
    history = await cursor.to_list(length=limit)
    for h in history:
        h["_id"] = str(h["_id"])
    return history

# --- Admin History ---
async def get_all_transactions_by_user(
    db: AsyncIOMotorDatabase, 
    user_id: str, 
    page: int, 
    limit: int, 
    date_filter: Optional[str] = None, 
    type: Optional[CreditType] = None, 
    source: Optional[CreditSource] = None
):
    if not ObjectId.is_valid(user_id):
        return []
    
    query: dict[str, Any] = {"user_id": ObjectId(user_id)}

    # add filter by type and source
    if type:
        query["type"] = type
    if source:
        query["source"] = source

    # Apply Date Filter
    if date_filter:
        try:
            start_date = datetime.strptime(date_filter, "%Y-%m-%d")
            end_date = start_date + timedelta(days=1)
            query["created_at"] = {"$gte": start_date, "$lt": end_date}
        except ValueError:
            pass

    skip = (page - 1) * limit
    cursor = db["credit_transactions"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    
    history = await cursor.to_list(length=limit)
    for h in history:
        h["_id"] = str(h["_id"])
    return history

async def delete_transaction(db: AsyncIOMotorDatabase, tx_id: str):
    """
    Deletes a transaction log.
    NOTE: This does NOT revert the user's balance. It only removes the record.
    """
    if not ObjectId.is_valid(tx_id):
        return False
        
    result = await db["credit_transactions"].delete_one({"_id": ObjectId(tx_id)})
    return result.deleted_count > 0

# --- 4. Get Eligibility Status (For UI) ---
async def get_earning_status(db: AsyncIOMotorDatabase, user_id: str, source: CreditSource):
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        return None

    start_of_today = get_start_of_today_utc()

    # A. Daily Credits (Sum of credits earned)
    if source == CreditSource.DAILY:
        user_cap = user.get("daily_credit_cap", 10)
        
        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "source": CreditSource.DAILY,
                    "created_at": {"$gte": start_of_today}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_earned": {"$sum": "$amount"}
                }
            }
        ]
        
        result = await db["credit_transactions"].aggregate(pipeline).to_list(length=1)
        total_earned = result[0]["total_earned"] if result else 0
        
        eligible = total_earned < user_cap
        remaining = max(0, user_cap - total_earned)
        
        return {
            "source": source,
            "eligible": eligible,
            "message": "Available" if eligible else "Daily limit reached",
            "current_usage": total_earned,
            "limit": user_cap,
            "remaining": remaining
        }

    # B. Single Action Rewards (Socials)
    elif source == CreditSource.SOCIALS:
        exists = await db["credit_transactions"].find_one({
            "user_id": ObjectId(user_id),
            "source": source,
            "created_at": {"$gte": start_of_today}
        })
        
        eligible = exists is None
        limit = 1
        current_usage = 1 if exists else 0
        
        return {
            "source": source,
            "eligible": eligible,
            "message": "Available" if eligible else "Already claimed in last 24h",
            "current_usage": current_usage,
            "limit": limit,
            "remaining": 1 if eligible else 0
        }

    # C. Default (Other sources like Signup/Admin aren't usually 'checked' by UI)
    return {
        "source": source,
        "eligible": True,
        "message": "Always available",
        "current_usage": 0,
        "limit": 0,
        "remaining": 0
    }
