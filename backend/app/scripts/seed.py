import logging

from app.models.admin import Admin
from app.models.exchange import Exchange
from app.security.password import hash_password

logger = logging.getLogger(__name__)

DEFAULT_EXCHANGES = [
    {
        "id": "bingx",
        "name": "BingX",
        "logo_url": "/logos/bingx.png",
        "enabled": True,
        "cron_schedule": "0 * * * *",
        "color": "#1E90FF",
        "config": {},
    },
    {
        "id": "exness",
        "name": "Exness",
        "logo_url": "/logos/exness.png",
        "enabled": True,
        "cron_schedule": "0 */2 * * *",
        "color": "#FF6B35",
        "config": {},
    },
]


async def seed_database() -> None:
    # Tạo tài khoản admin mặc định nếu chưa có
    admin_count = await Admin.count()
    if admin_count == 0:
        hashed = hash_password("admin123")
        await Admin(username="admin", password_hash=hashed).insert()
        logger.info("[Seed] Tạo tài khoản mặc định: admin / admin123")

    # Khởi tạo danh sách sàn giao dịch
    collection = Exchange.get_motor_collection()
    for ex in DEFAULT_EXCHANGES:
        await collection.update_one(
            {"id": ex["id"]},
            {"$setOnInsert": ex},
            upsert=True,
        )
    logger.info("[Seed] Khởi tạo %d sàn giao dịch", len(DEFAULT_EXCHANGES))
