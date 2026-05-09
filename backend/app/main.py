import logging
from contextlib import asynccontextmanager

import motor.motor_asyncio
from beanie import init_beanie
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.jobs.scheduler import start_scheduler
from app.middleware.camel_case import CamelCaseMiddleware
from app.models.admin import Admin
from app.models.community_member import CommunityMember
from app.models.daily_commission import DailyCommission
from app.models.exchange import Exchange
from app.models.referred_user import ReferredUser
from app.models.sync_log import SyncLog
from app.routes import auth, exchanges, members, stats, sync, users
from app.scripts.seed import seed_database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động: kết nối MongoDB, seed dữ liệu, chạy scheduler
    logger.info("[DB] Kết nối MongoDB: %s", settings.mongodb_uri)
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_uri)
    await init_beanie(
        database=client.get_default_database(),
        document_models=[Admin, Exchange, ReferredUser, SyncLog, DailyCommission, CommunityMember],
    )
    logger.info("[DB] Kết nối thành công")

    await seed_database()
    await start_scheduler()

    yield

    # Tắt: dừng scheduler
    from app.jobs.scheduler import scheduler
    if scheduler.running:
        scheduler.shutdown()
    logger.info("[Server] Đã tắt scheduler")


app = FastAPI(
    title="Refs Dashboard API",
    description="API quản lý người dùng giới thiệu qua các sàn giao dịch crypto",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,        # http://localhost:3000
        "http://refs_frontend:3000",   # Docker internal
        "http://frontend:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CamelCaseMiddleware)

app.include_router(auth.router)
app.include_router(exchanges.router)
app.include_router(users.router)
app.include_router(members.router)
app.include_router(stats.router)
app.include_router(sync.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
