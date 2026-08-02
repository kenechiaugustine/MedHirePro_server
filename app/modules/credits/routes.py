from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.core.database import get_database
from app.core.security import get_current_user_id
from app.modules.credits import schemas, service, enums
from fastapi import Query
from datetime import date
from typing import Optional

router = APIRouter()

# 1. Earn Credits (Protected)
@router.post("/earn")
async def earn_credits(
    payload: schemas.EarnCreditRequest,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    # Validation: Ensure user isn't trying to 'earn' via spending sources
    if payload.source in [enums.CreditSource.ACCESS, enums.CreditSource.SPEND]:
        raise HTTPException(status_code=400, detail="Invalid source for earning")

    # 1. Check Limits (Rolling Window)
    await service.check_earning_eligibility(db, user_id, payload.source, payload.amount)

    # 2. Process
    return await service.process_transaction(
        db, user_id, payload.amount, enums.CreditType.EARN, payload.source
    )

# 2. Spend Credits (Protected)
@router.post("/spend")
async def spend_credits(
    payload: schemas.SpendCreditRequest,
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    return await service.process_transaction(
        db, user_id, payload.amount, enums.CreditType.SPEND, payload.source, payload.description
    )

# 3. Get History
@router.get("/history", response_model=List[schemas.CreditTransactionResponse])
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50000),
    date: Optional[date] = Query(None, description="Filter by date (YYYY-MM-DD)"),
    user_id: str = Depends(get_current_user_id),
    type: Optional[enums.CreditType] = Query(None),
    source: Optional[enums.CreditSource] = Query(None),
    db = Depends(get_database)
):
    # Convert date object to string if present
    date_str = str(date) if date else None
    return await service.get_user_history(db, user_id, page, limit, date_str, type, source)


@router.get("/eligibility", response_model=schemas.EarningEligibilityResponse)
async def check_eligibility(
    source: enums.CreditSource, # Query param
    user_id: str = Depends(get_current_user_id),
    db = Depends(get_database)
):
    status = await service.get_earning_status(db, user_id, source)
    if not status:
        raise HTTPException(status_code=404, detail="User not found")
    return status
