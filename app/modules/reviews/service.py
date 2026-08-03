from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Optional
from app.modules.user import service as user_service

async def create_review(db: AsyncIOMotorDatabase, review_data: dict) -> dict:
    result = await db["reviews"].insert_one(review_data)
    created = await db["reviews"].find_one({"_id": result.inserted_id})
    created["_id"] = str(created["_id"])
    return created

async def get_all_reviews(
    db: AsyncIOMotorDatabase, 
    page: int = 1, 
    limit: int = 10
) -> tuple[List[dict], int]:
    total_count = await db["reviews"].count_documents({})
    skip = (page - 1) * limit
    cursor = db["reviews"].find().sort("created_at", -1).skip(skip).limit(limit)
    reviews = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        # Resolve user details dynamically
        user_id = doc.get("user_id")
        user_doc = await user_service.get_user_by_id(db, user_id)
        if user_doc:
            doc["user_details"] = user_doc
        reviews.append(doc)
    return reviews, total_count

async def update_review_visibility(
    db: AsyncIOMotorDatabase, 
    review_id: str, 
    is_public: bool
) -> Optional[dict]:
    from datetime import datetime, timezone
    result = await db["reviews"].update_one(
        {"_id": ObjectId(review_id)},
        {
            "$set": {
                "is_public": is_public,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    if result.matched_count == 0:
        return None
        
    doc = await db["reviews"].find_one({"_id": ObjectId(review_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
        # Resolve user details dynamically
        user_id = doc.get("user_id")
        user_doc = await user_service.get_user_by_id(db, user_id)
        if user_doc:
            doc["user_details"] = user_doc
    return doc
