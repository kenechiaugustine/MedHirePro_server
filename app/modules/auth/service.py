from google.oauth2 import id_token
from google.auth.transport import requests
from app.core.config import settings
from app.core.security import verify_password, get_password_hash
from app.modules.user.service import get_user_by_email
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

async def authenticate_user(db: AsyncIOMotorDatabase, email: str, password: str):
    # 1. Check if user exists
    user = await get_user_by_email(db, email)
    if not user:
        return None
    
    # 2. Check if user has a password (might be a Google-only account)
    if not user.get("password_hash"):
        return None 
        
    # 3. Verify Password
    if not verify_password(password, user["password_hash"]):
        return None
        
    return user

async def change_user_password(db: AsyncIOMotorDatabase, user_id: str, old_password: str, new_password: str):
    # 1. Get User
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if not user:
        return False, "User not found"
        
    # 2. Verify Old Password (if set)
    # If user has no password (e.g. Google auth only), they must use forgot password flow or set one first.
    # But for "Change Password", we assume they know the old one.
    current_hash = user.get("password_hash")
    if not current_hash:
        return False, "User has no password set. Use 'Forgot Password' or social login."
        
    if not verify_password(old_password, current_hash):
        return False, "Incorrect old password"

    # 3. Hash New Password
    new_hash = get_password_hash(new_password)
    
    # 4. Update User
    result = await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password_hash": new_hash}}
    )
    
    return result.modified_count > 0, "Password updated successfully"

def verify_google_token(token: str):
    try:
        # Verify the token against Google's servers
        id_info = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        return id_info
    except ValueError:
        return None