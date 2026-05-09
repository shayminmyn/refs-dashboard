from datetime import datetime
from math import ceil
from typing import Optional

from fastapi import APIRouter, Query
from pymongo import ASCENDING, DESCENDING

from app.middleware.auth import CurrentAdmin
from app.models.referred_user import ReferredUser

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("")
async def list_users(
    _: CurrentAdmin,
    exchange: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    status: Optional[str] = Query(None),
    sort_by: str = Query("registered_at", alias="sortBy"),
    sort_dir: str = Query("desc", alias="sortDir"),
):
    # Xây dựng bộ lọc MongoDB
    query_filter = {}

    if exchange:
        query_filter["exchange_id"] = exchange

    if status in ("active", "inactive"):
        query_filter["status"] = status

    if search:
        query_filter["$or"] = [
            {"username": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"user_id": {"$regex": search, "$options": "i"}},
        ]

    if from_date or to_date:
        date_filter = {}
        if from_date:
            date_filter["$gte"] = datetime.fromisoformat(from_date)
        if to_date:
            date_filter["$lte"] = datetime.fromisoformat(to_date)
        query_filter["registered_at"] = date_filter

    sort_order = ASCENDING if sort_dir == "asc" else DESCENDING
    skip = (page - 1) * limit

    collection = ReferredUser.get_motor_collection()

    total = await collection.count_documents(query_filter)
    cursor = (
        collection.find(query_filter, {"raw_data": 0})
        .sort(sort_by, sort_order)
        .skip(skip)
        .limit(limit)
    )
    users = await cursor.to_list(length=limit)

    # Chuyển ObjectId sang string
    for u in users:
        u["_id"] = str(u["_id"])

    return {
        "data": users,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": ceil(total / limit) if total else 1,
        },
    }
