from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.modules.user.schemas import UserResponse

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    comment: str = Field(..., min_length=5, description="Detailed review text")

class ReviewResponse(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    rating: int
    comment: str
    is_public: bool = False
    created_at: datetime
    updated_at: datetime
    user_details: Optional[UserResponse] = None

    class Config:
        populate_by_name = True
