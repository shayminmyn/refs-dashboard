from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.middleware.auth import CurrentAdmin
from app.models.sync_log import SyncLog
from app.services.sync_service import sync_exchange

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.get("/logs")
async def get_logs(
    _: CurrentAdmin,
    exchange: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    query = SyncLog.find()
    if exchange:
        query = SyncLog.find(SyncLog.exchange_id == exchange)

    logs = await query.sort("-started_at").limit(limit).to_list()
    return [
        {
            "_id": str(log.id),
            "exchange_id": log.exchange_id,
            "started_at": log.started_at,
            "finished_at": log.finished_at,
            "status": log.status,
            "records_upserted": log.records_upserted,
            "error": log.error,
        }
        for log in logs
    ]


@router.post("/{exchange_id}")
async def trigger_sync(exchange_id: str, _: CurrentAdmin):
    try:
        result = await sync_exchange(exchange_id)
        return {"success": True, "records_upserted": result}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
