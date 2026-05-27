import cloudinary
import cloudinary.uploader
import os
import uuid
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings
from app.modules.media.models import MediaModel

# Configure Cloudinary if credentials are provided
cloudinary_configured = False
cloud_name = settings.CLOUDINARY_CLOUD_NAME
api_key = settings.CLOUDINARY_API_KEY
api_secret = settings.CLOUDINARY_API_SECRET

if cloud_name and api_key and api_secret:
    # Ensure they are not dummy placeholder values
    if "your_cloudinary" not in cloud_name and cloud_name.strip() != "":
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        cloudinary_configured = True

if not cloudinary_configured:
    print("WARNING: Cloudinary credentials not configured. Using local uploads/media fallback.")


async def upload_media_file(db: AsyncIOMotorDatabase, user_id: str, file: UploadFile) -> dict:
    """
    Uploads a file to Cloudinary or falls back to local disk storage.
    Saves metadata to MongoDB.
    """
    # Read file content
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}{ext}"
    
    url = ""
    public_id = ""
    
    if cloudinary_configured:
        try:
            # Upload file bytes to Cloudinary
            result = cloudinary.uploader.upload(
                content,
                folder="medhirepro",
                public_id=unique_id,
                resource_type="auto"
            )
            url = result.get("secure_url")
            public_id = result.get("public_id")
        except Exception as e:
            # Fallback to local on upload failure or raise error
            print(f"Cloudinary upload failed: {e}. Falling back to local.")
            url = ""
            
    # Local fallback if not uploaded to Cloudinary
    if not url:
        upload_dir = "uploads/media"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            # URL relative to host
            url = f"/uploads/media/{filename}"
            public_id = f"local_{unique_id}_{filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file locally: {str(e)}")
            
    # Save to MongoDB
    media_doc = MediaModel.new_media(
        user_id=ObjectId(user_id) if ObjectId.is_valid(user_id) else user_id,
        url=url,
        public_id=public_id,
        filename=file.filename or "unknown",
        mimetype=file.content_type or "application/octet-stream",
        size=len(content)
    )
    
    res = await db["media"].insert_one(media_doc)
    media_doc["_id"] = str(res.inserted_id)
    if isinstance(media_doc["user_id"], ObjectId):
        media_doc["user_id"] = str(media_doc["user_id"])
        
    return media_doc


async def get_media_by_id(db: AsyncIOMotorDatabase, media_id: str) -> dict:
    """
    Retrieves media metadata by ID.
    """
    if not ObjectId.is_valid(media_id):
        return None
    media = await db["media"].find_one({"_id": ObjectId(media_id)})
    if media:
        media["_id"] = str(media["_id"])
        media["user_id"] = str(media["user_id"])
    return media


async def delete_media_file(db: AsyncIOMotorDatabase, media_id: str, user_id: str, is_admin: bool = False) -> bool:
    """
    Deletes media asset from storage (Cloudinary or local disk) and deletes DB metadata.
    Checks ownership unless requesting user is Admin.
    """
    if not ObjectId.is_valid(media_id):
        return False
        
    media = await db["media"].find_one({"_id": ObjectId(media_id)})
    if not media:
        return False
        
    # Check ownership
    owner_id = str(media["user_id"])
    if owner_id != user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this media asset")
        
    public_id = media.get("public_id", "")
    
    # 1. Remove from host/storage
    if public_id.startswith("local_"):
        # Local file deletion
        # Format: local_uuid_filename
        parts = public_id.split("_", 2)
        if len(parts) >= 3:
            filename = parts[2]
            file_path = os.path.join("uploads/media", filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Failed to delete local file {file_path}: {e}")
    else:
        # Cloudinary deletion
        if cloudinary_configured and public_id:
            try:
                cloudinary.uploader.destroy(public_id)
            except Exception as e:
                print(f"Cloudinary deletion failed for public_id {public_id}: {e}")
                
    # 2. Delete from MongoDB
    res = await db["media"].delete_one({"_id": ObjectId(media_id)})
    return res.deleted_count > 0
