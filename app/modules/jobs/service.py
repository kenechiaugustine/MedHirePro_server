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
        if isinstance(serialized["posted_by"], ObjectId):
            serialized["posted_by"] = str(serialized["posted_by"])
        elif isinstance(serialized["posted_by"], dict):
            if "_id" in serialized["posted_by"]:
                serialized["posted_by"]["_id"] = str(serialized["posted_by"]["_id"])
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
    serialized = serialize_doc(created)
    if serialized is None:
        raise RuntimeError("Failed to retrieve job listing after creation")
    return serialized

async def get_job_listing_by_id(db: AsyncIOMotorDatabase, job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single job listing by ID with natively populated posted_by details using MongoDB aggregation."""
    if not ObjectId.is_valid(job_id):
        return None
    pipeline = [
        {"$match": {"_id": ObjectId(job_id)}},
        {
            "$lookup": {
                "from": "users",
                "localField": "posted_by",
                "foreignField": "_id",
                "as": "poster_details"
            }
        },
        {
            "$addFields": {
                "posted_by": {
                    "$let": {
                        "vars": {"poster": {"$arrayElemAt": ["$poster_details", 0]}},
                        "in": {
                            "$cond": {
                                "if": {"$not": ["$$poster"]},
                                "then": "$posted_by",
                                "else": {
                                    "_id": "$$poster._id",
                                    "full_name": "$$poster.full_name",
                                    "facility_name": "$$poster.facility_name",
                                    "avatar_url": "$$poster.avatar_url",
                                    "role": "$$poster.role",
                                    "is_verified": {"$ifNull": ["$$poster.is_verified", False]}
                                }
                            }
                        }
                    }
                }
            }
        },
        {
            "$project": {
                "poster_details": 0
            }
        }
    ]
    cursor = db["job_listings"].aggregate(pipeline)
    docs = await cursor.to_list(length=1)
    if not docs:
        return None
    return serialize_doc(docs[0])

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
    """Retrieves list of job listings with dynamic filters, pagination, and natively populated posted_by details using MongoDB aggregation."""
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
    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "users",
                "localField": "posted_by",
                "foreignField": "_id",
                "as": "poster_details"
            }
        },
        {
            "$addFields": {
                "posted_by": {
                    "$let": {
                        "vars": {"poster": {"$arrayElemAt": ["$poster_details", 0]}},
                        "in": {
                            "$cond": {
                                "if": {"$not": ["$$poster"]},
                                "then": "$posted_by",
                                "else": {
                                    "_id": "$$poster._id",
                                    "full_name": "$$poster.full_name",
                                    "facility_name": "$$poster.facility_name",
                                    "avatar_url": "$$poster.avatar_url",
                                    "role": "$$poster.role",
                                    "is_verified": {"$ifNull": ["$$poster.is_verified", False]}
                                }
                            }
                        }
                    }
                }
            }
        },
        {
            "$project": {
                "poster_details": 0
            }
        }
    ]
    cursor = db["job_listings"].aggregate(pipeline)
    docs = await cursor.to_list(length=limit)
    serialized = [serialize_doc(d) for d in docs]
    return [s for s in serialized if s is not None]

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
    """Retrieves list of job listings with dynamic filters, pagination, total applicant counts, and natively populated posted_by details using MongoDB aggregation."""
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
        # Join with users for posted_by details
        {
            "$lookup": {
                "from": "users",
                "localField": "posted_by",
                "foreignField": "_id",
                "as": "poster_details"
            }
        },
        # Project total_applicants and populated posted_by based on lookups
        {
            "$addFields": {
                "total_applicants": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$app_count.count", 0]},
                        0
                    ]
                },
                "posted_by": {
                    "$let": {
                        "vars": {"poster": {"$arrayElemAt": ["$poster_details", 0]}},
                        "in": {
                            "$cond": {
                                "if": {"$not": ["$$poster"]},
                                "then": "$posted_by",
                                "else": {
                                    "_id": "$$poster._id",
                                    "full_name": "$$poster.full_name",
                                    "facility_name": "$$poster.facility_name",
                                    "avatar_url": "$$poster.avatar_url",
                                    "role": "$$poster.role",
                                    "is_verified": {"$ifNull": ["$$poster.is_verified", False]}
                                }
                            }
                        }
                    }
                }
            }
        },
        # Project out the temporary aggregation fields
        {
            "$project": {
                "app_count": 0,
                "poster_details": 0
            }
        }
    ]

    cursor = db["job_listings"].aggregate(pipeline)
    docs = await cursor.to_list(length=limit)
    serialized = [serialize_doc(d) for d in docs]
    return [s for s in serialized if s is not None]

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
