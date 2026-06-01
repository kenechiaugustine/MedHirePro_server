from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional, List, Any
from app.modules.user.enums import UserRole
from app.modules.credits import service as credits_service
from app.modules.credits.enums import CreditType, CreditSource

async def get_all_users(
    db: AsyncIOMotorDatabase,
    page: int = 1,
    limit: int = 10,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[dict]:
    """
    Fetch all users with filtering, search, and pagination.
    """
    query: dict[str, Any] = {}
    
    if role:
        query["role"] = role
        
    if is_active is not None:
        query["is_active"] = is_active
        
    if search:
        # Case-insensitive search on email, full name, or facility name
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
            {"facility_name": {"$regex": search, "$options": "i"}}
        ]
        
    skip = (page - 1) * limit
    cursor = db["users"].find(query).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    
def _format_user(user: dict) -> dict:
    """
    Ensures user dictionary matches the UserResponse schema fields exactly,
    providing fallback defaults for older or incomplete database records.
    """
    user["_id"] = str(user["_id"])
    if "referred_by" in user and user["referred_by"]:
        user["referred_by"] = str(user["referred_by"])
        
    # Populate robust defaults
    user["credit_balance"] = user.get("credit_balance") if user.get("credit_balance") is not None else 0
    user["daily_credit_cap"] = user.get("daily_credit_cap") if user.get("daily_credit_cap") is not None else 20
    user["is_active"] = user.get("is_active") if user.get("is_active") is not None else True
    user["is_deleted"] = user.get("is_deleted") if user.get("is_deleted") is not None else False
    user["onboarding_status"] = user.get("onboarding_status") if user.get("onboarding_status") is not None else "pending"
    user["is_verified"] = user.get("is_verified") if user.get("is_verified") is not None else False
    user["referred_count"] = user.get("referred_count") if user.get("referred_count") is not None else 0
    return user

async def get_all_users(
    db: AsyncIOMotorDatabase,
    page: int = 1,
    limit: int = 10,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None
) -> List[dict]:
    """
    Fetch all users with filtering, search, and pagination.
    """
    query: dict[str, Any] = {}
    
    if role:
        query["role"] = role
        
    if is_active is not None:
        query["is_active"] = is_active
        
    if search:
        # Case-insensitive search on email, full name, or facility name
        query["$or"] = [
            {"email": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
            {"facility_name": {"$regex": search, "$options": "i"}}
        ]
        
    skip = (page - 1) * limit
    cursor = db["users"].find(query).skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    
    return [_format_user(u) for u in users]

async def get_user_credits_history(
    db: AsyncIOMotorDatabase,
    user_id: str,
    page: int = 1,
    limit: int = 10,
    date_filter: Optional[str] = None,
    type: Optional[CreditType] = None,
    source: Optional[CreditSource] = None
) -> List[dict]:
    """
    Fetch credits transaction history for a specific user.
    """
    return await credits_service.get_all_transactions_by_user(
        db=db,
        user_id=user_id,
        page=page,
        limit=limit,
        date_filter=date_filter,
        type=type,
        source=source
    )

async def get_user_referrals(
    db: AsyncIOMotorDatabase,
    user_id: str,
    page: int = 1,
    limit: int = 10
) -> List[dict]:
    """
    Fetch all users referred by a specific user.
    """
    if not ObjectId.is_valid(user_id):
        return []
        
    skip = (page - 1) * limit
    cursor = db["users"].find({"referred_by": ObjectId(user_id)}).skip(skip).limit(limit)
    referred_users = await cursor.to_list(length=limit)
    
    return [_format_user(u) for u in referred_users]


async def reassign_job_owner(
    db: AsyncIOMotorDatabase,
    job_id: str,
    new_owner_id: str,
    new_owner_role: str
) -> Optional[dict]:
    """
    Reassigns the posted_by and poster_type fields of a job listing to a new user.
    """
    from datetime import datetime, timezone
    if not ObjectId.is_valid(job_id) or not ObjectId.is_valid(new_owner_id):
        return None
        
    result = await db["job_listings"].update_one(
        {"_id": ObjectId(job_id)},
        {
            "$set": {
                "posted_by": ObjectId(new_owner_id),
                "poster_type": new_owner_role,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    if result.matched_count == 0:
        return None
        
    updated = await db["job_listings"].find_one({"_id": ObjectId(job_id)})
    if updated:
        from app.modules.jobs.service import serialize_doc
        return serialize_doc(updated)
    return None

