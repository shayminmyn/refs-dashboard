"""
CommunityMember — người dùng từ cộng đồng (Telegram, Discord, ...)
Mỗi member có thể liên kết với 0..N sàn giao dịch (exchange_links).
"""

from datetime import datetime
from typing import List, Literal, Optional
from beanie import Document
from pydantic import Field
from pymongo import IndexModel, ASCENDING


class ExchangeLink:
    """Nhúng inline — không phải Document riêng."""
    pass


from pydantic import BaseModel


class ExchangeLink(BaseModel):
    exchange_id: str
    # UID của member trên sàn đó (lấy từ ReferredUser.user_id)
    exchange_user_id: str
    # Ghi chú tuỳ chọn (vd: "tài khoản chính")
    note: str = ""
    linked_at: datetime = Field(default_factory=datetime.utcnow)


class CommunityMember(Document):
    """
    Người dùng cộng đồng (Telegram, ...).
    platform: nguồn (telegram | discord | other)
    platform_id: ID duy nhất trên platform (telegram user_id, ...)
    """
    platform: Literal["telegram", "discord", "other"] = "telegram"
    platform_id: str                        # UID duy nhất trên platform
    username: str = ""                      # @username Telegram hoặc display name
    full_name: str = ""
    phone: str = ""
    notes: str = ""
    tags: List[str] = Field(default_factory=list)
    exchange_links: List[ExchangeLink] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "community_members"
        indexes = [
            IndexModel([("platform", ASCENDING), ("platform_id", ASCENDING)], unique=True),
            IndexModel([("username", ASCENDING)]),
            IndexModel([("exchange_links.exchange_id", ASCENDING)]),
            IndexModel([("exchange_links.exchange_user_id", ASCENDING)]),
        ]
