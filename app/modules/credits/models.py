from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from app.modules.credits.enums import CreditType, CreditSource

class CreditTransactionModel:
    @staticmethod
    def new_transaction(user_id: ObjectId, amount: int, type: CreditType, source: CreditSource, description: Optional[str] = None) -> dict:
        return {
            "user_id": user_id,  # Stored as ObjectId in Service
            "amount": amount,
            "type": type,
            "source": source,
            "description": description,
            "created_at": datetime.now(timezone.utc)
        }
