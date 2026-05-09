"""
API quản lý Community Members (người dùng từ cộng đồng Telegram, v.v.)
"""

from datetime import datetime
from math import ceil
from typing import List, Literal, Optional

from beanie import PydanticObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING

from app.middleware.auth import CurrentAdmin
from app.models.community_member import CommunityMember, ExchangeLink
from app.models.referred_user import ReferredUser

router = APIRouter(prefix="/api/members", tags=["members"])


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class ExchangeLinkIn(BaseModel):
    exchange_id: str
    exchange_user_id: str
    note: str = ""


class MemberCreate(BaseModel):
    platform: Literal["telegram", "discord", "other"] = "telegram"
    platform_id: str
    username: str = ""
    full_name: str = ""
    phone: str = ""
    notes: str = ""
    tags: List[str] = []
    exchange_links: List[ExchangeLinkIn] = []


class MemberUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize(m: CommunityMember) -> dict:
    return {
        "_id": str(m.id),
        "platform": m.platform,
        "platform_id": m.platform_id,
        "username": m.username,
        "full_name": m.full_name,
        "phone": m.phone,
        "notes": m.notes,
        "tags": m.tags,
        "is_active": m.is_active,
        "exchange_links": [
            {
                "exchange_id": lnk.exchange_id,
                "exchange_user_id": lnk.exchange_user_id,
                "note": lnk.note,
                "linked_at": lnk.linked_at,
            }
            for lnk in m.exchange_links
        ],
        "created_at": m.created_at,
        "updated_at": m.updated_at,
    }


async def _fetch_or_404(member_id: str) -> CommunityMember:
    try:
        oid = PydanticObjectId(member_id)
    except Exception:
        raise HTTPException(status_code=400, detail="member_id không hợp lệ")
    m = await CommunityMember.get(oid)
    if not m:
        raise HTTPException(status_code=404, detail="Không tìm thấy member")
    return m


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("")
async def list_members(
    _: CurrentAdmin,
    platform: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", alias="sortBy"),
    sort_dir: str = Query("desc", alias="sortDir"),
):
    collection = CommunityMember.get_motor_collection()
    filt: dict = {}

    if platform:
        filt["platform"] = platform
    if is_active is not None:
        filt["is_active"] = is_active
    if exchange:
        filt["exchange_links.exchange_id"] = exchange
    if search:
        filt["$or"] = [
            {"username": {"$regex": search, "$options": "i"}},
            {"full_name": {"$regex": search, "$options": "i"}},
            {"platform_id": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": search, "$options": "i"}}},
        ]

    sort_order = ASCENDING if sort_dir == "asc" else DESCENDING
    skip = (page - 1) * limit
    total = await collection.count_documents(filt)
    cursor = collection.find(filt).sort(sort_by, sort_order).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])

    return {
        "data": docs,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": ceil(total / limit) if total else 1,
        },
    }


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_member(_: CurrentAdmin, body: MemberCreate):
    existing = await CommunityMember.find_one(
        {"platform": body.platform, "platform_id": body.platform_id}
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Member đã tồn tại trên {body.platform} với ID '{body.platform_id}'",
        )

    links = [
        ExchangeLink(
            exchange_id=lnk.exchange_id,
            exchange_user_id=lnk.exchange_user_id,
            note=lnk.note,
        )
        for lnk in body.exchange_links
    ]

    member = CommunityMember(
        platform=body.platform,
        platform_id=body.platform_id,
        username=body.username,
        full_name=body.full_name,
        phone=body.phone,
        notes=body.notes,
        tags=body.tags,
        exchange_links=links,
    )
    await member.insert()
    return _serialize(member)


# ── Get one ───────────────────────────────────────────────────────────────────

@router.get("/{member_id}")
async def get_member(_: CurrentAdmin, member_id: str):
    m = await _fetch_or_404(member_id)
    return _serialize(m)


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{member_id}")
async def update_member(_: CurrentAdmin, member_id: str, body: MemberUpdate):
    m = await _fetch_or_404(member_id)
    if body.username is not None:
        m.username = body.username
    if body.full_name is not None:
        m.full_name = body.full_name
    if body.phone is not None:
        m.phone = body.phone
    if body.notes is not None:
        m.notes = body.notes
    if body.tags is not None:
        m.tags = body.tags
    if body.is_active is not None:
        m.is_active = body.is_active
    m.updated_at = datetime.utcnow()
    await m.save()
    return _serialize(m)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{member_id}", status_code=204)
async def delete_member(_: CurrentAdmin, member_id: str):
    m = await _fetch_or_404(member_id)
    await m.delete()


# ── Link exchange ─────────────────────────────────────────────────────────────

@router.post("/{member_id}/links")
async def add_exchange_link(_: CurrentAdmin, member_id: str, body: ExchangeLinkIn):
    m = await _fetch_or_404(member_id)
    for lnk in m.exchange_links:
        if lnk.exchange_id == body.exchange_id and lnk.exchange_user_id == body.exchange_user_id:
            raise HTTPException(
                status_code=409,
                detail=f"Liên kết {body.exchange_id}/{body.exchange_user_id} đã tồn tại",
            )
    m.exchange_links.append(
        ExchangeLink(
            exchange_id=body.exchange_id,
            exchange_user_id=body.exchange_user_id,
            note=body.note,
        )
    )
    m.updated_at = datetime.utcnow()
    await m.save()
    return _serialize(m)


@router.delete("/{member_id}/links/{exchange_id}/{exchange_user_id}", status_code=204)
async def remove_exchange_link(
    _: CurrentAdmin, member_id: str, exchange_id: str, exchange_user_id: str
):
    m = await _fetch_or_404(member_id)
    before = len(m.exchange_links)
    m.exchange_links = [
        lnk for lnk in m.exchange_links
        if not (lnk.exchange_id == exchange_id and lnk.exchange_user_id == exchange_user_id)
    ]
    if len(m.exchange_links) == before:
        raise HTTPException(status_code=404, detail="Không tìm thấy liên kết này")
    m.updated_at = datetime.utcnow()
    await m.save()


# ── Stats cho 1 member (tổng hợp từ tất cả exchange đã link) ─────────────────

@router.get("/{member_id}/stats")
async def member_stats(_: CurrentAdmin, member_id: str):
    m = await _fetch_or_404(member_id)
    if not m.exchange_links:
        return {"total_deposit": 0, "total_volume": 0, "total_commission": 0, "links": []}

    collection = ReferredUser.get_motor_collection()
    link_details = []
    grand = {"total_deposit": 0.0, "total_volume": 0.0, "total_commission": 0.0}

    for lnk in m.exchange_links:
        doc = await collection.find_one(
            {"exchange_id": lnk.exchange_id, "user_id": lnk.exchange_user_id},
            {"total_deposit": 1, "total_volume": 1, "total_commission": 1, "status": 1, "username": 1},
        )
        detail = {
            "exchange_id": lnk.exchange_id,
            "exchange_user_id": lnk.exchange_user_id,
            "note": lnk.note,
            "total_deposit": doc.get("total_deposit", 0) if doc else 0,
            "total_volume": doc.get("total_volume", 0) if doc else 0,
            "total_commission": doc.get("total_commission", 0) if doc else 0,
            "status": doc.get("status", "unknown") if doc else "not_found",
            "exchange_username": doc.get("username", "") if doc else "",
        }
        grand["total_deposit"] += detail["total_deposit"]
        grand["total_volume"] += detail["total_volume"]
        grand["total_commission"] += detail["total_commission"]
        link_details.append(detail)

    return {**grand, "links": link_details}


# ── Lookup exchange user trước khi link (kiểm tra tồn tại trong DB) ───────────

@router.get("/lookup/{exchange_id}/{exchange_user_id}")
async def lookup_exchange_user(
    _: CurrentAdmin,
    exchange_id: str,
    exchange_user_id: str,
):
    collection = ReferredUser.get_motor_collection()
    doc = await collection.find_one(
        {"exchange_id": exchange_id, "user_id": exchange_user_id},
        {"_id": 0, "user_id": 1, "username": 1, "email": 1,
         "total_deposit": 1, "total_volume": 1, "total_commission": 1, "status": 1},
    )
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy user '{exchange_user_id}' trên sàn '{exchange_id}' trong DB",
        )
    return doc
