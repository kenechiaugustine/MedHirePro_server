from datetime import datetime, timezone
from bson import ObjectId

class MediaModel:
    @staticmethod
    def new_media(
        user_id: ObjectId,
        url: str,
        public_id: str,
        filename: str,
        mimetype: str,
        size: int,
    ) -> dict:
        return {
            "user_id": user_id,
            "url": url,
            "public_id": public_id,
            "filename": filename,
            "mimetype": mimetype,
            "size": size,
            "created_at": datetime.now(timezone.utc)
        }
