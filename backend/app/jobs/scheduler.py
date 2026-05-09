import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.adapters.registry import get_adapter
from app.models.exchange import Exchange
from app.services.sync_service import sync_exchange

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def _run_sync(exchange_id: str) -> None:
    logger.info("[Scheduler] Bắt đầu sync %s", exchange_id)
    try:
        count = await sync_exchange(exchange_id)
        logger.info("[Scheduler] %s sync xong — %d bản ghi", exchange_id, count)
    except Exception as exc:
        logger.error("[Scheduler] %s sync lỗi: %s", exchange_id, exc)


def _make_job(exchange_id: str):
    """Tạo coroutine function cho job của mỗi sàn."""
    async def job():
        await _run_sync(exchange_id)
    job.__name__ = f"sync_{exchange_id}"
    return job


async def start_scheduler() -> None:
    """Đọc lịch từ MongoDB và đăng ký cronjob cho từng sàn enabled."""
    exchanges = await Exchange.find(Exchange.enabled == True).to_list()

    job_count = 0
    for ex in exchanges:
        if get_adapter(ex.exchange_id) is None:
            logger.warning(
                "[Scheduler] Bỏ qua %s — không có adapter (sàn đã tạm gỡ khỏi app)",
                ex.exchange_id,
            )
            continue
        parts = ex.cron_schedule.split()
        if len(parts) != 5:
            logger.warning("[Scheduler] Lịch không hợp lệ cho %s: %s", ex.exchange_id, ex.cron_schedule)
            continue

        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
        )
        scheduler.add_job(
            _make_job(ex.exchange_id),
            trigger=trigger,
            id=f"sync_{ex.exchange_id}",
            replace_existing=True,
        )
        job_count += 1
        logger.info("[Scheduler] Đăng ký sync %s theo lịch: %s", ex.exchange_id, ex.cron_schedule)

    scheduler.start()
    logger.info("[Scheduler] Đã khởi động %d job", job_count)
