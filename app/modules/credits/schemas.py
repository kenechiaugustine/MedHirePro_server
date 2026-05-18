from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.modules.credits.enums import CreditType, CreditSource

class EarnCreditRequest(BaseModel):
    amount: int
    source: CreditSource  # Must be one of the Enums

class SpendCreditRequest(BaseModel):
    amount: int
    source: CreditSource = CreditSource.SPEND
    description: Optional[str] = None

class CreditTransactionResponse(BaseModel):
    id: str = Field(alias="_id")
    amount: int
    type: CreditType
    source: CreditSource
    created_at: datetime
    description: Optional[str] = None

    class Config:
        populate_by_name = True


class EarningEligibilityResponse(BaseModel):
    source: CreditSource
    eligible: bool
    message: str
    current_usage: int  # How much earned/times done in last 24h
    limit: int          # The cap
    remaining: int      # limit - current_usage
