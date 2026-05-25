from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_database
from app.core.security import create_access_token, create_refresh_token, validate_refresh_token, get_password_hash, get_current_user_id
from app.modules.user import schemas as user_schemas
from app.modules.auth import schemas as auth_schemas
from app.modules.auth import service as auth_service
from app.modules.user import service as user_service
from app.modules.referral import service as referral_service
from app.modules.user.models import UserModel
from app.modules.user.enums import UserRole
from app.modules.credits.models import CreditTransactionModel
from app.modules.credits.enums import CreditType, CreditSource
from bson import ObjectId

router = APIRouter()

@router.post("/register/professional", response_model=auth_schemas.TokenResponse)
async def register_professional(
    payload: user_schemas.ProfessionalRegister,
    db = Depends(get_database)
):
    # Check if email exists
    existing_user = await user_service.get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered. Try logging in."
        )

    # Hash Password
    hashed_password = get_password_hash(payload.password)
    
    # Generate unique referral code for the new user
    new_referral_code = await referral_service.generate_unique_referral_code(db)

    # Create User
    new_user_data = UserModel.new_user(
        email=payload.email,
        role=UserRole.PROFESSIONAL,
        full_name=payload.full_name,
        specialty=payload.specialty,
        password_hash=hashed_password,
        employment_status=payload.employment_status,
        current_workplace=payload.current_workplace,
        referral_code=new_referral_code,
        referred_by=None,
    )
    user = await user_service.create_user(db, new_user_data)

    # Log Signup Bonus
    tx = CreditTransactionModel.new_transaction(
        user_id=ObjectId(user["_id"]),
        amount=2,
        type=CreditType.EARN,
        source=CreditSource.SIGNUP,
        description="Welcome Bonus"
    )
    await db["credit_transactions"].insert_one(tx)

    # Apply Referral Code fail-silently if provided
    if payload.referred_by_code:
        try:
            await referral_service.apply_referral_code(db, str(user["_id"]), payload.referred_by_code)
        except Exception:
            # Registration succeeds, but referral fields remain null and no referral bonus credits are given
            pass

    user_id = str(user["_id"])
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "user_role": UserRole.PROFESSIONAL
    }


@router.post("/register/institute", response_model=auth_schemas.TokenResponse)
async def register_institute(
    payload: user_schemas.InstituteRegister,
    db = Depends(get_database)
):
    # Check if email exists
    existing_user = await user_service.get_user_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail="Email already registered. Try logging in."
        )

    # Hash Password
    hashed_password = get_password_hash(payload.password)
    
    # Generate unique referral code for the new user
    new_referral_code = await referral_service.generate_unique_referral_code(db)

    # Create User
    new_user_data = UserModel.new_user(
        email=payload.email,
        role=UserRole.INSTITUTE,
        facility_name=payload.facility_name,
        password_hash=hashed_password,
        referral_code=new_referral_code,
        referred_by=None,
    )
    user = await user_service.create_user(db, new_user_data)

    # Log Signup Bonus
    tx = CreditTransactionModel.new_transaction(
        user_id=ObjectId(user["_id"]),
        amount=2,
        type=CreditType.EARN,
        source=CreditSource.SIGNUP,
        description="Welcome Bonus"
    )
    await db["credit_transactions"].insert_one(tx)

    # Apply Referral Code fail-silently if provided
    if payload.referred_by_code:
        try:
            await referral_service.apply_referral_code(db, str(user["_id"]), payload.referred_by_code)
        except Exception:
            # Registration succeeds, but referral fields remain null and no referral bonus credits are given
            pass

    user_id = str(user["_id"])
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "user_role": UserRole.INSTITUTE
    }


@router.post("/authenticate-with-google", response_model=auth_schemas.TokenResponse)
async def authenticate_google(
    payload: auth_schemas.GoogleLoginRequest,
    db = Depends(get_database)
):
    # Verify Google Token
    google_user = auth_service.verify_google_token(payload.id_token)
    if not google_user:
        raise HTTPException(status_code=400, detail="Invalid Google Token")

    email = google_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")
    user = await user_service.get_user_by_email(db, email)

    if not user:
        # Generate unique referral code for the new user
        new_referral_code = await referral_service.generate_unique_referral_code(db)

        # Create new Google User (defaults to professional)
        new_user_data = UserModel.new_user(
            email=email,
            role=UserRole.PROFESSIONAL,
            full_name=google_user.get("name"),
            avatar_url=google_user.get("picture"),
            google_id=google_user.get("sub"),
            referral_code=new_referral_code,
            referred_by=None,
        )
        user = await user_service.create_user(db, new_user_data)

        # Log Signup Bonus
        tx = CreditTransactionModel.new_transaction(
            user_id=ObjectId(user["_id"]),
            amount=2,
            type=CreditType.EARN,
            source=CreditSource.SIGNUP,
            description="Welcome Bonus"
        )
        await db["credit_transactions"].insert_one(tx)

        # Apply Referral Code fail-silently if provided
        if payload.referred_by_code:
            try:
                await referral_service.apply_referral_code(db, str(user["_id"]), payload.referred_by_code)
            except Exception:
                # Registration succeeds, but referral fields remain null and no referral bonus credits are given
                pass
    else:
        # (Optional) Update Google ID if user registered with email before but now uses Google
        if not user.get("google_id"):
            await db["users"].update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "google_id": google_user.get("sub"),
                    "avatar_url": user.get("avatar_url") or google_user.get("picture"),
                    "is_active": True,
                }}
            )

    user_id = str(user["_id"])
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "user_role": user.get("role", UserRole.PROFESSIONAL)
    }

@router.post("/login", response_model=auth_schemas.TokenResponse)
async def login(
    payload: user_schemas.UserLogin,
    db = Depends(get_database)
):
    user = await auth_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = str(user["_id"])
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "user_role": user.get("role", UserRole.PROFESSIONAL)
    }

@router.post("/change-password")
async def change_password(
    payload: auth_schemas.ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    success, message = await auth_service.change_user_password(
        db, user_id, payload.old_password, payload.new_password
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

@router.post("/admin/login", response_model=auth_schemas.TokenResponse)
async def admin_login(
    payload: user_schemas.UserLogin,
    db = Depends(get_database)
):
    # 1. Authenticate (Check Email/Pass)
    user = await auth_service.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # 2. Authorization (Check Role)
    if user.get("role") != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: Admins only",
        )
    
    user_id = str(user["_id"])
    return {
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
        "user_role": UserRole.ADMIN
    }

@router.post("/refresh-token", response_model=auth_schemas.TokenResponse)
async def refresh_token(
    refresh_token: str,
    db = Depends(get_database)
):
    # 1. Validate the refresh token string directly
    user_id = validate_refresh_token(refresh_token)
    
    # 2. Check if user still exists
    user = await user_service.get_user_by_id(db, user_id)
    if not user:
         raise HTTPException(status_code=401, detail="User no longer exists")

    # 3. Create new set of auth tokens
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "user_role": user.get("role", UserRole.PROFESSIONAL)
    }