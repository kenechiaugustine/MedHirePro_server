from datetime import datetime, timedelta, timezone
from typing import Union, Any
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # <--- Import this
import bcrypt
from app.core.config import settings
from app.core.database import get_database  # <--- This was missing/causing the error
from app.modules.user import service as user_service

# 1. Change the Security Scheme
# OLD: oauth2_scheme = OAuth2PasswordBearer(tokenUrl=...)
security = HTTPBearer() 

# ... Password functions (verify_password, get_password_hash) remain the same ...
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def validate_refresh_token(token: str) -> str:
    """
    Decodes a refresh token and returns the user_id (sub).
    Raises HTTPException if invalid or wrong token type.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        # Explicitly check if this is a refresh token
        if user_id is None or token_type != "refresh":
            raise credentials_exception
            
        return user_id
    except JWTError:
        raise credentials_exception

# ... Token creation functions (create_access_token, create_refresh_token) remain the same ...
def create_access_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# 2. Update the Dependency to extract token from HTTPAuthorizationCredentials
async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract the token string from the Bearer object
    token = credentials.credentials 

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception

async def get_current_admin(
    user_id: str = Depends(get_current_user_id), 
    db = Depends(get_database)
):
    """
    Dependency to ensure the request is coming from an Administrator.
    """
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not enough permissions"
        )
    
    return user
