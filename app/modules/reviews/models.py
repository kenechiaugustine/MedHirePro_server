from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

class ReviewModel:
    @staticmethod
    def new_review(user_id: str, rating: int, comment: str) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "rating": rating,
            "comment": comment,
            "is_public": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
