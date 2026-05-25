from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.modules.auth.routes import router as auth_router
from app.modules.user.routes import router as user_router
from app.modules.credits.routes import router as credits_router
from app.modules.referral.routes import router as referral_router

@asynccontextmanager
async def lifespan(app: FastAPI):
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

# Routes
@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(user_router, prefix=f"{settings.API_V1_STR}/user", tags=["User"])
app.include_router(referral_router, prefix=f"{settings.API_V1_STR}/referral", tags=["Referral"])
app.include_router(credits_router, prefix=f"{settings.API_V1_STR}/credits", tags=["Credits"])