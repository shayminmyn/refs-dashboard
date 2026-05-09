from datetime import datetime
from typing import Any, Dict, Literal, Optional
from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel, ASCENDING, DESCENDING


class ReferredUser(Document):
    exchange_id: str
    user_id: str
    username: str = ""
    email: str = ""
    registered_at: Optional[datetime] = None
    total_deposit: float = 0.0
    total_volume: float = 0.0
    total_commission: float = 0.0
    status: Literal["active", "inactive"] = "active"
    last_synced_at: datetime = Field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "referred_users"
        indexes = [
            IndexModel([("exchange_id", ASCENDING), ("user_id", ASCENDING)], unique=True),
            IndexModel([("exchange_id", ASCENDING)]),
            IndexModel([("registered_at", DESCENDING)]),
        ]
