from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.modules.jobs.enums import JobType
from app.modules.applications.enums import ApplicationStatus

def serialize_doc(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Helper to convert MongoDB ObjectIds to strings for Pydantic serialization."""
    if not doc:
        return None
    serialized = dict(doc)
    if "_id" in serialized:
        serialized["_id"] = str(serialized["_id"])
    if "candidate_id" in serialized and serialized["candidate_id"]:
        serialized["candidate_id"] = str(serialized["candidate_id"])
        
    vacancy_id = serialized.get("vacancy_id")
    if vacancy_id:
        if isinstance(vacancy_id, dict):
            if "_id" in vacancy_id:
                vacancy_id["_id"] = str(vacancy_id["_id"])
            if "posted_by" in vacancy_id:
                if isinstance(vacancy_id["posted_by"], ObjectId):
                    vacancy_id["posted_by"] = str(vacancy_id["posted_by"])
                elif isinstance(vacancy_id["posted_by"], dict):
                    if "_id" in vacancy_id["posted_by"]:
                        vacancy_id["posted_by"]["_id"] = str(vacancy_id["posted_by"]["_id"])
        else:
            serialized["vacancy_id"] = str(vacancy_id)
            
    return serialized

async def populate_application_vacancy(db: AsyncIOMotorDatabase, doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Serializes the application doc and populates its vacancy_id with full job details and candidate details."""
    if not doc:
        return None
    serialized = serialize_doc(doc)
    if not serialized:
        return None
        
    vacancy_id = doc.get("vacancy_id")
    
    if vacancy_id:
        vacancy_id_str = str(vacancy_id)
        from app.modules.jobs import service as jobs_service
        job = await jobs_service.get_job_listing_by_id(db, vacancy_id_str)
        if job:
            serialized["vacancy_id"] = job

    # Populate candidate details
    candidate_id = doc.get("candidate_id")
    if candidate_id:
        candidate_id_str = str(candidate_id)
        from app.modules.user import service as user_service
        user = await user_service.get_user_by_id(db, candidate_id_str)
        if user:
            serialized["candidate_details"] = {
                "id": str(user.get("_id") or user.get("id")),
                "full_name": user.get("full_name"),
                "email": user.get("email"),
                "phone_number": user.get("phone_number"),
                "specialty": user.get("specialty"),
                "avatar_url": user.get("avatar_url"),
                "is_verified": user.get("is_verified", False),
                "employment_status": user.get("employment_status"),
                "current_workplace": user.get("current_workplace"),
                "is_intern": user.get("is_intern"),
                "licence_number": user.get("licence_number"),
                "licence_expiry": user.get("licence_expiry"),
                "licence_document_url": user.get("licence_document_url"),
                "degree_document_url": user.get("degree_document_url"),
                "id_document_url": user.get("id_document_url"),
                "school_or_placement_letter_url": user.get("school_or_placement_letter_url"),
            }
                
    return serialized

async def create_application(db: AsyncIOMotorDatabase, candidate_id: str, app_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new application with robust defaults and populated vacancy details."""
    doc = dict(app_data)
    
    # Defensive fallbacks
    if "is_shortlisted" not in doc:
        doc["is_shortlisted"] = False
    if "is_accepted" not in doc:
        doc["is_accepted"] = False
    if "application_status" not in doc:
        doc["application_status"] = ApplicationStatus.SUBMITTED
    if "created_at" not in doc:
        doc["created_at"] = datetime.now(timezone.utc)
    if "updated_at" not in doc:
        doc["updated_at"] = datetime.now(timezone.utc)

    if "vacancy_type" not in doc or not doc["vacancy_type"]:
        from app.modules.jobs import service as jobs_service
        job = await jobs_service.get_job_listing_by_id(db, str(doc["vacancy_id"]))
        if job:
            doc["vacancy_type"] = job.get("job_type")

    doc["candidate_id"] = ObjectId(candidate_id)
    doc["vacancy_id"] = ObjectId(doc["vacancy_id"])
    result = await db["applications"].insert_one(doc)
    created = await db["applications"].find_one({"_id": result.inserted_id})
    populated = await populate_application_vacancy(db, created)
    if populated is None:
        raise RuntimeError("Failed to retrieve application after creation")
    return populated

async def get_application_by_id(db: AsyncIOMotorDatabase, application_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single application by ID with populated vacancy details."""
    if not ObjectId.is_valid(application_id):
        return None
    doc = await db["applications"].find_one({"_id": ObjectId(application_id)})
    return await populate_application_vacancy(db, doc)

async def get_applications(
    db: AsyncIOMotorDatabase,
    candidate_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
    vacancy_type: Optional[JobType] = None,
    is_shortlisted: Optional[bool] = None,
    is_accepted: Optional[bool] = None,
    application_status: Optional[ApplicationStatus] = None,
    page: int = 1,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Queries applications dynamically with pagination and natively populates vacancy details using an aggregation pipeline."""
    query: Dict[str, Any] = {}
    if candidate_id:
        if not ObjectId.is_valid(candidate_id):
            return []
        query["candidate_id"] = ObjectId(candidate_id)
    if vacancy_id:
        if not ObjectId.is_valid(vacancy_id):
            return []
        query["vacancy_id"] = ObjectId(vacancy_id)
    if vacancy_type is not None:
        query["vacancy_type"] = vacancy_type
    if is_shortlisted is not None:
        query["is_shortlisted"] = is_shortlisted
    if is_accepted is not None:
        query["is_accepted"] = is_accepted
    if application_status is not None:
        query["application_status"] = application_status

    skip = (page - 1) * limit

    pipeline = [
        {"$match": query},
        {"$sort": {"created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
        # MongoDB Native Population Equivalent ($lookup join)
        {
            "$lookup": {
                "from": "job_listings",
                "let": {"vacancy_oid": "$vacancy_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$eq": ["$_id", "$$vacancy_oid"]}}},
                    # Lookup the poster user for the job listing
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
                ],
                "as": "vacancy_details"
            }
        },
        # Extract first element from vacancy_details and project to vacancy_id
        {
            "$addFields": {
                "vacancy_id": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$vacancy_details", 0]},
                        "$vacancy_id"
                    ]
                }
            }
        },
        # Join with users collection for candidate details
        {
            "$lookup": {
                "from": "users",
                "localField": "candidate_id",
                "foreignField": "_id",
                "as": "candidate_details_arr"
            }
        },
        {
            "$addFields": {
                "candidate_details": {
                    "$let": {
                        "vars": {
                            "candidate": {"$arrayElemAt": ["$candidate_details_arr", 0]}
                        },
                        "in": {
                            "id": {"$toString": "$$candidate._id"},
                            "full_name": "$$candidate.full_name",
                            "email": "$$candidate.email",
                            "phone_number": "$$candidate.phone_number",
                            "specialty": "$$candidate.specialty",
                            "avatar_url": "$$candidate.avatar_url",
                            "is_verified": {"$ifNull": ["$$candidate.is_verified", False]},
                            "employment_status": "$$candidate.employment_status",
                            "current_workplace": "$$candidate.current_workplace",
                            "is_intern": "$$candidate.is_intern",
                            "licence_number": "$$candidate.licence_number",
                            "licence_expiry": "$$candidate.licence_expiry",
                            "licence_document_url": "$$candidate.licence_document_url",
                            "degree_document_url": "$$candidate.degree_document_url",
                            "id_document_url": "$$candidate.id_document_url",
                            "school_or_placement_letter_url": "$$candidate.school_or_placement_letter_url"
                        }
                    }
                }
            }
        },
        # Project out temporary arrays
        {
            "$project": {
                "vacancy_details": 0,
                "candidate_details_arr": 0
            }
        }
    ]

    cursor = db["applications"].aggregate(pipeline)
    docs = await cursor.to_list(length=limit)
    serialized = [serialize_doc(d) for d in docs]
    return [s for s in serialized if s is not None]

async def has_user_applied(db: AsyncIOMotorDatabase, candidate_id: str, vacancy_id: str) -> bool:
    """Checks if a candidate has already applied to a particular vacancy."""
    if not ObjectId.is_valid(candidate_id) or not ObjectId.is_valid(vacancy_id):
        return False
    count = await db["applications"].count_documents({
        "candidate_id": ObjectId(candidate_id),
        "vacancy_id": ObjectId(vacancy_id)
    })
    return count > 0

async def get_user_application_for_vacancy(db: AsyncIOMotorDatabase, candidate_id: str, vacancy_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an application submitted by a candidate for a specific vacancy."""
    if not ObjectId.is_valid(candidate_id) or not ObjectId.is_valid(vacancy_id):
        return None
    doc = await db["applications"].find_one({
        "candidate_id": ObjectId(candidate_id),
        "vacancy_id": ObjectId(vacancy_id)
    })
    return serialize_doc(doc)

async def update_application_shortlist(db: AsyncIOMotorDatabase, application_id: str, is_shortlisted: bool) -> Optional[Dict[str, Any]]:
    """
    Sets shortlist flag.
    If shortlisted, updates status to Credentialing Review.
    If un-shortlisted and not yet accepted/declined, resets to Submitted.
    """
    if not ObjectId.is_valid(application_id):
        return None
    
    app = await db["applications"].find_one({"_id": ObjectId(application_id)})
    if not app:
        return None

    update_fields: Dict[str, Any] = {
        "is_shortlisted": is_shortlisted,
        "updated_at": datetime.now(timezone.utc)
    }

    # Status adjustments
    current_status = app.get("application_status", ApplicationStatus.SUBMITTED)
    if is_shortlisted:
        if current_status == ApplicationStatus.SUBMITTED:
            update_fields["application_status"] = ApplicationStatus.CREDENTIALING_REVIEW
    else:
        if current_status == ApplicationStatus.CREDENTIALING_REVIEW:
            update_fields["application_status"] = ApplicationStatus.SUBMITTED

    await db["applications"].update_one(
        {"_id": ObjectId(application_id)},
        {"$set": update_fields}
    )
    return await get_application_by_id(db, application_id)

async def update_application_acceptance(db: AsyncIOMotorDatabase, application_id: str, is_accepted: bool) -> Optional[Dict[str, Any]]:
    """
    Sets acceptance flag.
    If accepted, sets shortlist to True and status to Accepted.
    If un-accepted, reverts status to Credentialing Review or Submitted depending on shortlist flag.
    """
    if not ObjectId.is_valid(application_id):
        return None

    app = await db["applications"].find_one({"_id": ObjectId(application_id)})
    if not app:
        return None

    update_fields: Dict[str, Any] = {
        "is_accepted": is_accepted,
        "updated_at": datetime.now(timezone.utc)
    }

    if is_accepted:
        update_fields["is_shortlisted"] = True
        update_fields["application_status"] = ApplicationStatus.ACCEPTED
    else:
        # Revert
        was_shortlisted = app.get("is_shortlisted", False)
        if was_shortlisted:
            update_fields["application_status"] = ApplicationStatus.CREDENTIALING_REVIEW
        else:
            update_fields["application_status"] = ApplicationStatus.SUBMITTED

    await db["applications"].update_one(
        {"_id": ObjectId(application_id)},
        {"$set": update_fields}
    )
    return await get_application_by_id(db, application_id)

async def update_application_status(db: AsyncIOMotorDatabase, application_id: str, status: ApplicationStatus) -> Optional[Dict[str, Any]]:
    """Updates raw status directly (e.g. to DECLINED). Checks and maintains boolean flags."""
    if not ObjectId.is_valid(application_id):
        return None

    update_fields: Dict[str, Any] = {
        "application_status": status,
        "updated_at": datetime.now(timezone.utc)
    }

    if status == ApplicationStatus.ACCEPTED:
        update_fields["is_accepted"] = True
        update_fields["is_shortlisted"] = True
    elif status == ApplicationStatus.DECLINED:
        update_fields["is_accepted"] = False
    elif status == ApplicationStatus.CREDENTIALING_REVIEW:
        update_fields["is_accepted"] = False
        update_fields["is_shortlisted"] = True
    elif status == ApplicationStatus.SUBMITTED:
        update_fields["is_accepted"] = False
        update_fields["is_shortlisted"] = False

    await db["applications"].update_one(
        {"_id": ObjectId(application_id)},
        {"$set": update_fields}
    )
    return await get_application_by_id(db, application_id)
