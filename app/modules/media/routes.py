from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
import os
from app.core.database import get_database
from app.core.security import get_current_user_id
from app.modules.media import service
from app.modules.user import service as user_service

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(..., description="Select a file to upload"),
    upload_type: str = Form("document", description="Type of upload (picture or document)"),
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Uploads a single file to Cloudinary (or local storage fallback).
    Saves metadata in MongoDB.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided for upload"
        )

    filename = file.filename.lower()
    allowed_picture_exts = {".jpg", ".jpeg", ".png"}
    allowed_document_exts = {".pdf", ".docx", ".jpg", ".jpeg", ".png"}

    if upload_type == "picture":
        if not any(filename.endswith(ext) for ext in allowed_picture_exts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Only JPG and PNG are accepted for pictures."
            )
    elif upload_type == "document":
        if not any(filename.endswith(ext) for ext in allowed_document_exts):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Only PDF, DOCX, JPG, and PNG are accepted for documents."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid upload type specified."
        )
        
    asset = await service.upload_media_file(db, user_id, file)
    
    return {
        "message": "Successfully uploaded file",
        "media": asset
    }


@router.get("/{media_id}")
async def get_media_info(
    media_id: str,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Retrieves the metadata of a specific media resource.
    """
    media = await service.get_media_by_id(db, media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media resource not found"
        )
    return media


@router.delete("/{media_id}")
async def delete_media(
    media_id: str,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    """
    Deletes a media asset from storage and purges metadata from the database.
    Only the uploader or an Admin can delete the asset.
    """
    # Fetch current user to determine Admin privileges
    user = await user_service.get_user_by_id(db, user_id)
    is_admin = False
    if user and user.get("role") == "admin":
        is_admin = True
        
    success = await service.delete_media_file(db, media_id, user_id, is_admin=is_admin)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media resource not found"
        )
        
    return {"message": "Media resource deleted successfully"}
