from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str
    API_V1_STR: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    MONGODB_URL: str
    DATABASE_NAME: str
    GOOGLE_CLIENT_ID: str
    ADMIN_SECRET_KEY: str
    BACKEND_CORS_ORIGINS: list[str] = []

    class Config:
        env_file = ".env"

settings = Settings()