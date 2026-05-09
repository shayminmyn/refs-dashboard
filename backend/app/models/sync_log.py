from datetime import datetime
from typing import Literal, Optional
from beanie import Document
from pydantic import Field


class SyncLog(Document):
    exchange_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    status: Literal["running", "success", "failed"] = "running"
    records_upserted: int = 0
    error: Optional[str] = None

    class Settings:
        name = "sync_logs"
        indexes = ["exchange_id"]
