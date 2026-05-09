from datetime import datetime
from beanie import Document
from pydantic import Field


class Admin(Document):
    username: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "admins"
        indexes = ["username"]
