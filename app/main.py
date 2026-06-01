import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.modules.auth.routes import router as auth_router
from app.modules.user.routes import router as user_router
from app.modules.credits.routes import router as credits_router
from app.modules.referral.routes import router as referral_router
from app.modules.media.routes import router as media_router
from app.modules.onboarding.routes import router as onboarding_router
from app.modules.admin.routes import router as admin_router
from app.modules.jobs.routes import router as jobs_router

from app.modules.applications.routes import router as applications_router



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure local upload directories exist
    os.makedirs("uploads/media", exist_ok=True)
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure local upload directories exist
os.makedirs("uploads/media", exist_ok=True)

# Mount local uploads for fallback simulation
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Routes
@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(user_router, prefix=f"{settings.API_V1_STR}/user", tags=["User"])
app.include_router(referral_router, prefix=f"{settings.API_V1_STR}/referral", tags=["Referral"])
app.include_router(credits_router, prefix=f"{settings.API_V1_STR}/credits", tags=["Credits"])
app.include_router(media_router, prefix=f"{settings.API_V1_STR}/media", tags=["Media"])
app.include_router(onboarding_router, prefix=f"{settings.API_V1_STR}/onboarding", tags=["Onboarding"])
app.include_router(admin_router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])
app.include_router(jobs_router, prefix=f"{settings.API_V1_STR}/jobs", tags=["Job Listings"])
app.include_router(applications_router, prefix=f"{settings.API_V1_STR}/applications", tags=["Applications"])