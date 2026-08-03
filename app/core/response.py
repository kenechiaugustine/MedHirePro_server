import math
from typing import Generic, TypeVar, List, Any
from pydantic import BaseModel

T = TypeVar('T')

class PaginationMeta(BaseModel):
    perPage: int
    currentPage: int
    totalPage: int
    totalDocumentCount: int

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationMeta

class SingleResponse(BaseModel, Generic[T]):
    data: T

def create_paginated_response(items: List[Any], page: int, per_page: int, total_count: int) -> dict:
    total_page = math.ceil(total_count / per_page) if (per_page > 0 and total_count > 0) else 0
    return {
        "data": items,
        "pagination": {
            "perPage": per_page,
            "currentPage": page,
            "totalPage": total_page,
            "totalDocumentCount": total_count
        }
    }

def create_single_response(data: Any) -> dict:
    return {
        "data": data if data is not None else {}
    }
