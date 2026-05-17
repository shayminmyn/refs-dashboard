import logging
from datetime import datetime

from pymongo import UpdateOne

from app.adapters.base import GenericDailyCommission
from app.adapters.bingx import BingXDailyCommission
from app.adapters.registry import get_adapter
from app.models.daily_commission import DailyCommission
from app.models.referred_user import ReferredUser
from app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)

INITIAL_DAYS_BACK = 30   # lần đầu: lấy 30 ngày lịch sử
INCREMENTAL_DAYS_BACK = 3  # các lần sau: chỉ cập nhật 3 ngày gần nhất


async def _is_first_sync(exchange_id: str) -> bool:
    """Trả về True nếu chưa có bản ghi DailyCommission nào cho sàn này."""
    dc_collection = DailyCommission.get_motor_collection()
    count = await dc_collection.count_documents({"exchange_id": exchange_id}, limit=1)
    return count == 0


async def _sync_commissions(exchange_id: str, adapter, days_back: int) -> int:
    """
    Lấy hoa hồng theo days_back và upsert vào DailyCommission.
    Trả về số bản ghi đã xử lý.
    """
    raw_commissions = await adapter.fetch_daily_commissions_raw(days_back=days_back)
    if not raw_commissions:
        return 0

    dc_collection = DailyCommission.get_motor_collection()
    ops = []

    now = datetime.utcnow()
    for c in raw_commissions:
        if not isinstance(c, (BingXDailyCommission, GenericDailyCommission)):
            continue
        ops.append(UpdateOne(
            {
                "exchange_id": exchange_id,
                "user_id": str(c.uid),
                "commission_date": datetime.combine(c.commission_date, datetime.min.time()),
            },
            {
                "$set": {
                    "trading_volume": c.trading_volume,
                    "commission_volume": c.commission_volume,
                    "spot_volume": c.spot_volume,
                    "spot_commission": c.spot_commission,
                    "swap_volume": c.swap_volume,
                    "swap_commission": c.swap_commission,
                    "std_volume": c.std_volume,
                    "std_commission": c.std_commission,
                    "copy_volume": c.copy_volume,
                    "copy_commission": c.copy_commission,
                    "synced_at": now,
                },
                # Đặt exchange_id/user_id/commission_date khi insert lần đầu
                "$setOnInsert": {
                    "exchange_id": exchange_id,
                    "user_id": str(c.uid),
                    "commission_date": datetime.combine(c.commission_date, datetime.min.time()),
                },
            },
            upsert=True,
        ))

    if not ops:
        return 0

    result = await dc_collection.bulk_write(ops)
    # upserted_count: bản ghi mới; modified_count: bản ghi đã đổi giá trị thực
    # (synced_at dùng cùng giá trị `now` trong batch nên không inflate modified_count)
    return result.upserted_count + result.modified_count


async def _rollup_referred_user_totals_from_daily(exchange_id: str) -> int:
    """
    Ghi đè total_volume / total_commission trên referred_users = SUM toàn bộ
    daily_commissions của user đó trong Mongo (toàn bộ ngày đã sync tích luỹ).

    Chỉ update bản ghi đã tồn tại (exchange_id + user_id); không upsert user mới.
    """
    dc_collection = DailyCommission.get_motor_collection()
    ref_collection = ReferredUser.get_motor_collection()

    pipeline = [
        {"$match": {"exchange_id": exchange_id}},
        {
            "$group": {
                "_id": "$user_id",
                "total_volume": {"$sum": "$trading_volume"},
                "total_commission": {"$sum": "$commission_volume"},
            }
        },
    ]
    rows = await dc_collection.aggregate(pipeline).to_list(length=None)
    if not rows:
        return 0

    ops = [
        UpdateOne(
            {"exchange_id": exchange_id, "user_id": row["_id"]},
            {
                "$set": {
                    "total_volume": float(row["total_volume"] or 0),
                    "total_commission": float(row["total_commission"] or 0),
                }
            },
        )
        for row in rows
    ]
    await ref_collection.bulk_write(ops, ordered=False)
    logger.info(
        "[Sync] %s: rollup snapshot từ DailyCommission (%d user có ít nhất 1 ngày)",
        exchange_id,
        len(rows),
    )
    return len(rows)


async def sync_exchange(exchange_id: str) -> int:
    """
    Đồng bộ dữ liệu một sàn:
    - Lần đầu (chưa có DailyCommission): lấy toàn bộ 30 ngày lịch sử.
    - Các lần sau: chỉ cập nhật 3 ngày gần nhất (nhanh hơn, ít request API hơn).
    - BingX/Bitget: sau khi ghi DailyCommission, rollup total_volume / total_commission
      trên ReferredUser = SUM toàn bộ bản ghi daily của user trong Mongo (lịch sử tích luỹ).
    - Exness: giữ snapshot all-time từ API clients — không rollup (tránh ghi đè bằng cửa sổ DC hẹp).

    Trả về số người dùng đã upsert.
    """
    adapter = get_adapter(exchange_id)
    if not adapter:
        raise ValueError(f"Không tìm thấy adapter cho sàn: {exchange_id}")

    first_sync = await _is_first_sync(exchange_id)
    days_back = INITIAL_DAYS_BACK if first_sync else INCREMENTAL_DAYS_BACK
    sync_mode = "full (lần đầu)" if first_sync else f"incremental ({days_back} ngày)"
    logger.info("[Sync] %s — bắt đầu %s", exchange_id, sync_mode)

    log = SyncLog(exchange_id=exchange_id, started_at=datetime.utcnow(), status="running")
    await log.insert()

    try:
        # ── 1. Danh sách người dùng ───────────────────────────────────────────
        users = await adapter.fetch_referrals(commission_days=days_back)

        if users:
            collection = ReferredUser.get_motor_collection()
            ops = [
                UpdateOne(
                    {"exchange_id": exchange_id, "user_id": u.user_id},
                    {
                        "$set": {
                            "username": u.username,
                            "email": u.email,
                            "registered_at": u.registered_at,
                            "total_deposit": u.total_deposit,
                            "total_volume": u.total_volume,
                            "total_commission": u.total_commission,
                            "status": u.status,
                            "last_synced_at": datetime.utcnow(),
                            "raw_data": u.raw_data,
                        }
                    },
                    upsert=True,
                )
                for u in users
            ]
            await collection.bulk_write(ops)
            logger.info("[Sync] %s: upsert %d người dùng", exchange_id, len(users))

        # ── 2. Hoa hồng hàng ngày ─────────────────────────────────────────────
        commission_count = await _sync_commissions(exchange_id, adapter, days_back)
        logger.info(
            "[Sync] %s: %d bản ghi hoa hồng (%s)",
            exchange_id, commission_count, sync_mode,
        )

        # ── 2b. Snapshot volume/commission = tổng toàn bộ lịch sử daily trong DB ──
        if adapter.snapshot_totals_from_daily_rollup():
            await _rollup_referred_user_totals_from_daily(exchange_id)

        # ── 3. Cập nhật log ───────────────────────────────────────────────────
        log.finished_at = datetime.utcnow()
        log.status = "success"
        log.records_upserted = len(users)
        await log.save()

        logger.info(
            "[Sync] %s hoàn tất — %d users, %d commission entries",
            exchange_id, len(users), commission_count,
        )
        return len(users)

    except Exception as exc:
        log.finished_at = datetime.utcnow()
        log.status = "failed"
        log.error = str(exc)
        await log.save()
        logger.error("[Sync] %s thất bại: %s", exchange_id, exc)
        raise
