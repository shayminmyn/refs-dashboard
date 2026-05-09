from fastapi import APIRouter, HTTPException

from app.middleware.auth import CurrentAdmin
from app.models.exchange import Exchange

router = APIRouter(prefix="/api/exchanges", tags=["exchanges"])


@router.get("")
async def list_exchanges(_: CurrentAdmin):
    exchanges = await Exchange.find(Exchange.enabled == True).sort("name").to_list()
    return [
        {
            "id": ex.exchange_id,
            "name": ex.name,
            "logo_url": ex.logo_url,
            "color": ex.color,
            "enabled": ex.enabled,
            "cron_schedule": ex.cron_schedule,
        }
        for ex in exchanges
    ]


@router.get("/{exchange_id}")
async def get_exchange(exchange_id: str, _: CurrentAdmin):
    ex = await Exchange.find_one({"id": exchange_id})
    if not ex:
        raise HTTPException(status_code=404, detail="Sàn giao dịch không tồn tại")
    return {
        "id": ex.exchange_id,
        "name": ex.name,
        "logo_url": ex.logo_url,
        "color": ex.color,
        "enabled": ex.enabled,
        "cron_schedule": ex.cron_schedule,
    }
