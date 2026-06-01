from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.modules.jobs.enums import (
    JobType,
    JobStatus,
    RateType,
    ClinicalSetting,
    ClinicalSpecialty,
)

def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Helper to convert MongoDB ObjectIds to strings for Pydantic serialization."""
    if not doc:
        return None
    serialized = dict(doc)
    if "_id" in serialized:
        serialized["_id"] = str(serialized["_id"])
    if "posted_by" in serialized and serialized["posted_by"]:
        serialized["posted_by"] = str(serialized["posted_by"])
    return serialized

async def create_job_listing(db: AsyncIOMotorDatabase, posted_by: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a new job listing document with fallback defaults."""
    doc = dict(job_data)
    if "status" not in doc:
        doc["status"] = JobStatus.OPEN
    if "created_at" not in doc:
        doc["created_at"] = datetime.now(timezone.utc)
    if "updated_at" not in doc:
        doc["updated_at"] = datetime.now(timezone.utc)

    doc["posted_by"] = ObjectId(posted_by)
    result = await db["job_listings"].insert_one(doc)
    created = await db["job_listings"].find_one({"_id": result.inserted_id})
    return serialize_doc(created)

async def get_job_listing_by_id(db: AsyncIOMotorDatabase, job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single job listing by ID."""
    if not ObjectId.is_valid(job_id):
        return None
    doc = await db["job_listings"].find_one({"_id": ObjectId(job_id)})
    return serialize_doc(doc)

async def get_job_listings(
    db: AsyncIOMotorDatabase,
    posted_by: Optional[str] = None,
    job_type: Optional[JobType] = None,
    clinical_specialty: Optional[ClinicalSpecialty] = None,
    clinical_setting: Optional[ClinicalSetting] = None,
    status: Optional[JobStatus] = None,
    page: int = 1,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Retrieves list of job listings with dynamic filters and pagination."""
    query: Dict[str, Any] = {}
    if posted_by and ObjectId.is_valid(posted_by):
        query["posted_by"] = ObjectId(posted_by)
    if job_type is not None:
        query["job_type"] = job_type
    if clinical_specialty is not None:
        query["clinical_specialty"] = clinical_specialty
    if clinical_setting is not None:
        query["clinical_setting"] = clinical_setting
    if status is not None:
        query["status"] = status

    skip = (page - 1) * limit
    cursor = db["job_listings"].find(query).sort("created_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [serialize_doc(d) for d in docs]

async def get_job_listings_with_applicant_counts(
    db: AsyncIOMotorDatabase,
    posted_by: Optional[str] = None,
    job_type: Optional[JobType] = None,
    clinical_specialty: Optional[ClinicalSpecialty] = None,
    clinical_setting: Optional[ClinicalSetting] = None,
    status: Optional[JobStatus] = None,
    page: int = 1,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Retrieves list of job listings with dynamic filters, pagination, and total applicant counts using an aggregation pipeline."""
    match_query: Dict[str, Any] = {}
    if posted_by and ObjectId.is_valid(posted_by):
        match_query["posted_by"] = ObjectId(posted_by)
    if job_type is not None:
        match_query["job_type"] = job_type
    if clinical_specialty is not None:
        match_query["clinical_specialty"] = clinical_specialty
    if clinical_setting is not None:
        match_query["clinical_setting"] = clinical_setting
    if status is not None:
        match_query["status"] = status

    skip = (page - 1) * limit

    pipeline = [
        {"$match": match_query},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        # High-performance $lookup with subpipeline to count documents
        {
            "$lookup": {
                "from": "applications",
                "let": {"job_id": "$_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$vacancy_id", "$$job_id"]}}},
                    {"$count": "count"}
                ],
                "as": "app_count"
            }
        },
        # Project total_applicants based on subpipeline count
        {
            "$addFields": {
                "total_applicants": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$app_count.count", 0]},
                        0
                    ]
                }
            }
        },
        # Project out the app_count field
        {
            "$project": {
                "app_count": 0
            }
        }
    ]

    cursor = db["job_listings"].aggregate(pipeline)
    docs = await cursor.to_list(length=limit)
    return [serialize_doc(d) for d in docs]

async def update_job_listing(db: AsyncIOMotorDatabase, job_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Updates selected fields of a job listing."""
    if not ObjectId.is_valid(job_id):
        return None
    
    update_fields = {k: v for k, v in update_data.items() if v is not None}
    if not update_fields:
        return await get_job_listing_by_id(db, job_id)
        
    update_fields["updated_at"] = datetime.now(timezone.utc)
    
    result = await db["job_listings"].update_one(
        {"_id": ObjectId(job_id)},
        {"$set": update_fields}
    )
    if result.matched_count == 0:
        return None
    return await get_job_listing_by_id(db, job_id)

async def delete_job_listing(db: AsyncIOMotorDatabase, job_id: str) -> bool:
    """Hard-deletes a job listing from the database."""
    if not ObjectId.is_valid(job_id):
        return False
    result = await db["job_listings"].delete_one({"_id": ObjectId(job_id)})
    return result.deleted_count > 0
