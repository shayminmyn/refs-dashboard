from datetime import datetime
from typing import Dict
from beanie import Document
from pydantic import ConfigDict, Field


class Exchange(Document):
    """
    Tránh đặt tên field là 'id' trong Beanie Document vì Pydantic/Beanie
    dùng 'id' là alias của '_id' (ObjectId) → ValidationError khi load từ DB.
    Dùng 'exchange_id' thay thế.
    """
    model_config = ConfigDict(populate_by_name=True)

    exchange_id: str = Field(alias="id")   # lưu trong MongoDB dưới key "id"
    name: str
    logo_url: str = ""
    enabled: bool = True
    cron_schedule: str = "0 * * * *"
    color: str = "#6366f1"
    config: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "exchanges"
        use_state_management = True
