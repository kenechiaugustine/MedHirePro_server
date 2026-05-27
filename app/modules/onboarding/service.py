from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.onboarding.enums import OnboardingStatus
from app.modules.onboarding.models import OnboardingSubmissionModel
from app.modules.user import service as user_service

async def submit_onboarding(db: AsyncIOMotorDatabase, user_id: str, role: str, details: dict) -> dict:
    """
    Validates onboarding documents and fields, then inserts/updates onboarding submissions in MongoDB.
    Sets the user's onboarding_status to "submitted".
    """
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=400, detail="Invalid user ID")
        
    # 1. Conditional Validations based on Role
    if role == "professional":
        is_intern = details.get("is_intern", False)
        if not is_intern:
            # Fully licensed professional check
            if not details.get("licence_number") or not details.get("licence_expiry") or not details.get("licence_document_url"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="License number, expiration, and certificate document are required for fully licensed professionals"
                )
        else:
            # Intern check
            if not details.get("school_or_placement_letter_url"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Dean's letter or hospital residency/clinical placement letter is required for interns"
                )
    elif role == "institute":
        # All required fields are already validated by the Pydantic schema, but we double-check registration number
        if not details.get("business_registration_number") or not details.get("business_license_url"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business registration number and operating permit are required"
            )
            
    # 2. Check if a submission already exists
    existing_sub = await db["onboarding_submissions"].find_one({"user_id": ObjectId(user_id)})
    
    submission_doc = OnboardingSubmissionModel.new_submission(
        user_id=ObjectId(user_id),
        role=role,
        details=details
    )
    
    if existing_sub:
        # Overwrite the existing submission (supports resubmitting after rejection)
        await db["onboarding_submissions"].update_one(
            {"_id": existing_sub["_id"]},
            {"$set": submission_doc}
        )
        submission_doc["_id"] = str(existing_sub["_id"])
    else:
        # Create a new submission
        res = await db["onboarding_submissions"].insert_one(submission_doc)
        submission_doc["_id"] = str(res.inserted_id)
        
    # 3. Update User Onboarding status
    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "onboarding_status": OnboardingStatus.SUBMITTED.value,
            "updated_at": datetime.now(timezone.utc)
        }}
    )
    
    submission_doc["user_id"] = str(submission_doc["user_id"])
    return submission_doc


async def get_onboarding_status(db: AsyncIOMotorDatabase, user_id: str) -> Optional[dict]:
    """
    Fetches the onboarding submission metadata and status for a user.
    """
    if not ObjectId.is_valid(user_id):
        return None
        
    sub = await db["onboarding_submissions"].find_one({"user_id": ObjectId(user_id)})
    if sub:
        sub["_id"] = str(sub["_id"])
        sub["user_id"] = str(sub["user_id"])
        if sub.get("reviewed_by"):
            sub["reviewed_by"] = str(sub["reviewed_by"])
    return sub


async def list_pending_submissions(db: AsyncIOMotorDatabase, skip: int = 0, limit: int = 10) -> List[dict]:
    """
    Lists all onboarding submissions that are currently pending review (status = 'submitted').
    Enriches with user metadata.
    """
    cursor = db["onboarding_submissions"].find({"status": OnboardingStatus.SUBMITTED.value})
    # FIFO order: earliest submissions first
    cursor = cursor.sort("submitted_at", 1).skip(skip).limit(limit)
    
    submissions = await cursor.to_list(length=limit)
    res_list = []
    
    for sub in submissions:
        sub["_id"] = str(sub["_id"])
        sub["user_id"] = str(sub["user_id"])
        
        # Enrich with User Account details
        user = await db["users"].find_one({"_id": ObjectId(sub["user_id"])})
        if user:
            sub["user_info"] = {
                "email": user.get("email"),
                "full_name": user.get("full_name") or user.get("facility_name"),
                "avatar_url": user.get("avatar_url"),
                "role": user.get("role")
            }
        else:
            sub["user_info"] = None
            
        res_list.append(sub)
        
    return res_list


async def review_onboarding(
    db: AsyncIOMotorDatabase,
    submission_id: str,
    admin_id: str,
    action: str,
    rejection_reason: Optional[str] = None
) -> dict:
    """
    Approves or rejects an onboarding submission.
    Updates the submission state and synchronizes verified status + profile fields back to the User document.
    """
    if not ObjectId.is_valid(submission_id) or not ObjectId.is_valid(admin_id):
        raise HTTPException(status_code=400, detail="Invalid submission or admin ID")
        
    submission = await db["onboarding_submissions"].find_one({"_id": ObjectId(submission_id)})
    if not submission:
        raise HTTPException(status_code=404, detail="Onboarding submission not found")
        
    user_id = submission["user_id"]
    role = submission["role"]
    details = submission.get("details", {})
    
    # 1. Action validation
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be either 'approve' or 'reject'")
        
    if action == "reject" and not rejection_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rejection reason must be provided when rejecting a submission"
        )
        
    now = datetime.now(timezone.utc)
    
    # 2. Perform updates
    if action == "approve":
        # Approval flow
        await db["onboarding_submissions"].update_one(
            {"_id": ObjectId(submission_id)},
            {"$set": {
                "status": OnboardingStatus.APPROVED.value,
                "reviewed_at": now,
                "reviewed_by": ObjectId(admin_id),
                "rejection_reason": None
            }}
        )
        
        # Prepare profile sync updates
        user_updates = {
            "onboarding_status": OnboardingStatus.APPROVED.value,
            "is_verified": True,
            "updated_at": now
        }
        
        # Sync submission specific profile fields
        if role == "professional":
            if details.get("specialty"):
                user_updates["specialty"] = details["specialty"]
            if details.get("employment_status"):
                user_updates["employment_status"] = details["employment_status"]
            if details.get("current_workplace"):
                user_updates["current_workplace"] = details["current_workplace"]
        elif role == "institute":
            # For facility, facility name is preserved, but we could sync address details if needed.
            pass
            
        # Update user
        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": user_updates}
        )
        
    else:
        # Rejection flow
        await db["onboarding_submissions"].update_one(
            {"_id": ObjectId(submission_id)},
            {"$set": {
                "status": OnboardingStatus.REJECTED.value,
                "reviewed_at": now,
                "reviewed_by": ObjectId(admin_id),
                "rejection_reason": rejection_reason
            }}
        )
        
        # Update user status to rejected
        await db["users"].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "onboarding_status": OnboardingStatus.REJECTED.value,
                "is_verified": False,
                "updated_at": now
            }}
        )
        
    # Return updated submission
    updated_sub = await db["onboarding_submissions"].find_one({"_id": ObjectId(submission_id)})
    updated_sub["_id"] = str(updated_sub["_id"])
    updated_sub["user_id"] = str(updated_sub["user_id"])
    updated_sub["reviewed_by"] = str(updated_sub["reviewed_by"])
    
    return updated_sub
