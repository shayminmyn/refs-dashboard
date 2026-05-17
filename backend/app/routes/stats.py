from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from app.middleware.auth import CurrentAdmin
from app.models.daily_commission import DailyCommission
from app.models.exchange import Exchange
from app.models.referred_user import ReferredUser

router = APIRouter(prefix="/api/stats", tags=["stats"])

ALLOWED_METRICS = {"total_deposit", "total_volume", "total_commission"}

_METRIC_ALIASES = {
    "totalDeposit": "total_deposit",
    "totalVolume": "total_volume",
    "totalCommission": "total_commission",
}


def _normalize_metric(metric: str) -> str:
    return _METRIC_ALIASES.get(metric, metric)


def _parse_date_bounds(from_date: str, to_date: str) -> Tuple[datetime, datetime]:
    try:
        start = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(to_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="from và to phải là YYYY-MM-DD") from None
    if start > end:
        raise HTTPException(status_code=400, detail="from không được sau to")
    return start, end


def _validate_range_params(from_date: Optional[str], to_date: Optional[str]) -> Optional[Tuple[datetime, datetime]]:
    if from_date is None and to_date is None:
        return None
    if from_date is None or to_date is None:
        raise HTTPException(
            status_code=400,
            detail="Gửi cả query from và to (YYYY-MM-DD), hoặc bỏ cả hai (toàn thời gian).",
        )
    return _parse_date_bounds(from_date, to_date)


async def _overview_all_time() -> Dict[str, Any]:
    collection = ReferredUser.get_motor_collection()
    pipeline = [
        {
            "$group": {
                "_id": "$exchange_id",
                "total_deposit": {"$sum": "$total_deposit"},
                "total_volume": {"$sum": "$total_volume"},
                "total_commission": {"$sum": "$total_commission"},
                "total_users": {"$sum": 1},
                "active_users": {"$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}},
            }
        }
    ]
    rows = await collection.aggregate(pipeline).to_list(length=None)
    row_map = {row["_id"]: row for row in rows}
    exchanges = await Exchange.find(Exchange.enabled == True).sort("name").to_list()

    by_exchange = []
    for ex in exchanges:
        rid = ex.exchange_id
        if rid in row_map:
            row = row_map[rid]
            by_exchange.append(
                {
                    "exchange_id": rid,
                    "exchange_name": ex.name,
                    "color": ex.color,
                    "total_deposit": row["total_deposit"],
                    "total_volume": row["total_volume"],
                    "total_commission": row["total_commission"],
                    "total_users": row["total_users"],
                    "active_users": row["active_users"],
                }
            )
        else:
            by_exchange.append(
                {
                    "exchange_id": rid,
                    "exchange_name": ex.name,
                    "color": ex.color,
                    "total_deposit": 0,
                    "total_volume": 0,
                    "total_commission": 0,
                    "total_users": 0,
                    "active_users": 0,
                }
            )

    totals = {
        "total_deposit": sum(r["total_deposit"] for r in by_exchange),
        "total_volume": sum(r["total_volume"] for r in by_exchange),
        "total_commission": sum(r["total_commission"] for r in by_exchange),
        "total_users": sum(r["total_users"] for r in by_exchange),
        "active_users": sum(r["active_users"] for r in by_exchange),
    }
    return {"totals": totals, "by_exchange": by_exchange}


async def _overview_from_daily_commission(start: datetime, end: datetime, exchanges: List[Exchange]) -> Dict[str, Any]:
    dc_collection = DailyCommission.get_motor_collection()
    pipeline = [
        {"$match": {"commission_date": {"$gte": start, "$lte": end}}},
        {
            "$group": {
                "_id": "$exchange_id",
                "total_commission": {"$sum": "$commission_volume"},
                "total_volume": {"$sum": "$trading_volume"},
                "uids": {"$addToSet": "$user_id"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "exchange_id": "$_id",
                "total_commission": 1,
                "total_volume": 1,
                "total_users": {"$size": "$uids"},
                "active_users": {"$size": "$uids"},
                "total_deposit": {"$literal": 0},
            }
        },
    ]
    rows = await dc_collection.aggregate(pipeline).to_list(length=None)
    row_map = {r["exchange_id"]: r for r in rows}
    ex_map = {ex.exchange_id: ex for ex in exchanges}

    by_exchange = []
    for ex in exchanges:
        rid = ex.exchange_id
        if rid in row_map:
            r = row_map[rid]
            by_exchange.append(
                {
                    "exchange_id": rid,
                    "exchange_name": ex.name,
                    "color": ex.color,
                    "total_deposit": r["total_deposit"],
                    "total_volume": r["total_volume"],
                    "total_commission": r["total_commission"],
                    "total_users": r["total_users"],
                    "active_users": r["active_users"],
                }
            )
        else:
            by_exchange.append(
                {
                    "exchange_id": rid,
                    "exchange_name": ex.name,
                    "color": ex.color,
                    "total_deposit": 0,
                    "total_volume": 0,
                    "total_commission": 0,
                    "total_users": 0,
                    "active_users": 0,
                }
            )

    totals = {
        "total_deposit": sum(r["total_deposit"] for r in by_exchange),
        "total_volume": sum(r["total_volume"] for r in by_exchange),
        "total_commission": sum(r["total_commission"] for r in by_exchange),
        "total_users": sum(r["total_users"] for r in by_exchange),
        "active_users": sum(r["active_users"] for r in by_exchange),
    }
    return {"totals": totals, "by_exchange": by_exchange}


async def _overview_from_referred_registered(start: datetime, end: datetime, exchanges: List[Exchange]) -> Dict[str, Any]:
    collection = ReferredUser.get_motor_collection()
    pipeline = [
        {"$match": {"registered_at": {"$gte": start, "$lte": end}}},
        {
            "$group": {
                "_id": "$exchange_id",
                "total_deposit": {"$sum": "$total_deposit"},
                "total_volume": {"$sum": "$total_volume"},
                "total_commission": {"$sum": "$total_commission"},
                "total_users": {"$sum": 1},
                "active_users": {"$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}},
            }
        },
    ]
    rows = await collection.aggregate(pipeline).to_list(length=None)
    row_map = {row["_id"]: row for row in rows}
    by_exchange = []
    for ex in exchanges:
        rid = ex.exchange_id
        if rid in row_map:
            row = row_map[rid]
            by_exchange.append(
                {
                    "exchange_id": rid,
                    "exchange_name": ex.name,
                    "color": ex.color,
                    "total_deposit": row["total_deposit"],
                    "total_volume": row["total_volume"],
                    "total_commission": row["total_commission"],
                    "total_users": row["total_users"],
                    "active_users": row["active_users"],
                }
            )
        else:
            by_exchange.append(
                {
                    "exchange_id": rid,
                    "exchange_name": ex.name,
                    "color": ex.color,
                    "total_deposit": 0,
                    "total_volume": 0,
                    "total_commission": 0,
                    "total_users": 0,
                    "active_users": 0,
                }
            )

    totals = {
        "total_deposit": sum(r["total_deposit"] for r in by_exchange),
        "total_volume": sum(r["total_volume"] for r in by_exchange),
        "total_commission": sum(r["total_commission"] for r in by_exchange),
        "total_users": sum(r["total_users"] for r in by_exchange),
        "active_users": sum(r["active_users"] for r in by_exchange),
    }
    return {"totals": totals, "by_exchange": by_exchange}


@router.get("/overview")
async def overview(
    _: CurrentAdmin,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    bounds = _validate_range_params(from_date, to_date)
    if bounds is None:
        return await _overview_all_time()

    start, end = bounds
    exchanges = await Exchange.find(Exchange.enabled == True).sort("name").to_list()
    dc_collection = DailyCommission.get_motor_collection()
    dc_count = await dc_collection.count_documents({"commission_date": {"$gte": start, "$lte": end}})
    if dc_count > 0:
        return await _overview_from_daily_commission(start, end, exchanges)
    return await _overview_from_referred_registered(start, end, exchanges)


@router.get("/{exchange_id}/timeseries")
async def timeseries(
    exchange_id: str,
    _: CurrentAdmin,
    metric: str = Query("total_commission"),
    period: str = Query("day"),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    metric = _normalize_metric(metric)
    if metric not in ALLOWED_METRICS:
        raise HTTPException(
            status_code=400,
            detail=f"metric không hợp lệ. Cho phép: {sorted(ALLOWED_METRICS)} hoặc camelCase tương đương.",
        )

    bounds = _validate_range_params(from_date, to_date)

    dc_metric_map = {
        "total_commission": "commission_volume",
        "total_volume": "trading_volume",
        "total_deposit": "trading_volume",
    }

    dc_collection = DailyCommission.get_motor_collection()
    dc_match: Dict[str, Any] = {} if exchange_id == "all" else {"exchange_id": exchange_id}
    if bounds:
        dc_match["commission_date"] = {"$gte": bounds[0], "$lte": bounds[1]}

    dc_count = await dc_collection.count_documents(dc_match)

    # Giới hạn số điểm time-series chỉ khi có khoảng ngày — tránh cắt mất phần "gần đây"
    # khi All time (bounds=None): trả về toàn bộ bucket sau sort.
    def _series_limit() -> Optional[int]:
        if bounds is None:
            return None
        return 240 if period == "month" else 800

    series_cap = _series_limit()

    if dc_count > 0:
        dc_field = dc_metric_map[metric]

        if period == "month":
            group_id = {"year": {"$year": "$commission_date"}, "month": {"$month": "$commission_date"}}
        else:
            group_id = {
                "year": {"$year": "$commission_date"},
                "month": {"$month": "$commission_date"},
                "day": {"$dayOfMonth": "$commission_date"},
            }

        pipeline: List[Dict[str, Any]] = [
            {"$match": dc_match},
            {
                "$group": {
                    "_id": group_id,
                    "value": {"$sum": f"${dc_field}"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
        ]
        if series_cap is not None:
            pipeline.append({"$limit": series_cap})

        rows = await dc_collection.aggregate(pipeline).to_list(length=None)

    else:
        ref_collection = ReferredUser.get_motor_collection()
        match: Dict[str, Any] = {} if exchange_id == "all" else {"exchange_id": exchange_id}
        if bounds:
            match = {**match, "registered_at": {"$gte": bounds[0], "$lte": bounds[1]}}

        if period == "month":
            group_id = {"year": {"$year": "$registered_at"}, "month": {"$month": "$registered_at"}}
        else:
            group_id = {
                "year": {"$year": "$registered_at"},
                "month": {"$month": "$registered_at"},
                "day": {"$dayOfMonth": "$registered_at"},
            }

        pipeline = [
            {"$match": match},
            {
                "$group": {
                    "_id": group_id,
                    "value": {"$sum": f"${metric}"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}},
        ]
        if series_cap is not None:
            pipeline.append({"$limit": series_cap})

        rows = await ref_collection.aggregate(pipeline).to_list(length=None)

    result = []
    for row in rows:
        gid = row["_id"]
        if period == "month":
            date_str = f"{gid['year']}-{str(gid['month']).zfill(2)}"
        else:
            date_str = f"{gid['year']}-{str(gid['month']).zfill(2)}-{str(gid.get('day', 1)).zfill(2)}"
        result.append({"date": date_str, "value": row["value"], "count": row["count"]})

    return result


@router.get("/{exchange_id}/commission-breakdown")
async def commission_breakdown(exchange_id: str, _: CurrentAdmin):
    dc_collection = DailyCommission.get_motor_collection()
    match = {} if exchange_id == "all" else {"exchange_id": exchange_id}

    pipeline = [
        {"$match": match},
        {
            "$group": {
                "_id": None,
                "spot_commission": {"$sum": "$spot_commission"},
                "swap_commission": {"$sum": "$swap_commission"},
                "std_commission": {"$sum": "$std_commission"},
                "copy_commission": {"$sum": "$copy_commission"},
                "spot_volume": {"$sum": "$spot_volume"},
                "swap_volume": {"$sum": "$swap_volume"},
                "std_volume": {"$sum": "$std_volume"},
                "copy_volume": {"$sum": "$copy_volume"},
            }
        },
    ]

    rows = await dc_collection.aggregate(pipeline).to_list(length=1)
    if not rows:
        return {
            "spot": {"commission": 0, "volume": 0},
            "swap": {"commission": 0, "volume": 0},
            "std": {"commission": 0, "volume": 0},
            "copy": {"commission": 0, "volume": 0},
        }

    r = rows[0]
    return {
        "spot": {"commission": r["spot_commission"], "volume": r["spot_volume"]},
        "swap": {"commission": r["swap_commission"], "volume": r["swap_volume"]},
        "std": {"commission": r["std_commission"], "volume": r["std_volume"]},
        "copy": {"commission": r["copy_commission"], "volume": r["copy_volume"]},
    }


async def _exchange_stats_all_time(exchange_id: str) -> Dict[str, Any]:
    collection = ReferredUser.get_motor_collection()
    pipeline = [
        {"$match": {"exchange_id": exchange_id}},
        {
            "$group": {
                "_id": None,
                "total_deposit": {"$sum": "$total_deposit"},
                "total_volume": {"$sum": "$total_volume"},
                "total_commission": {"$sum": "$total_commission"},
                "total_users": {"$sum": 1},
                "active_users": {"$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}},
            }
        },
    ]
    rows = await collection.aggregate(pipeline).to_list(length=1)
    if not rows:
        return {
            "total_deposit": 0,
            "total_volume": 0,
            "total_commission": 0,
            "total_users": 0,
            "active_users": 0,
        }
    row = rows[0]
    return {
        "total_deposit": row["total_deposit"],
        "total_volume": row["total_volume"],
        "total_commission": row["total_commission"],
        "total_users": row["total_users"],
        "active_users": row["active_users"],
    }


async def _exchange_stats_from_daily(start: datetime, end: datetime, exchange_id: str) -> Dict[str, Any]:
    dc_collection = DailyCommission.get_motor_collection()
    pipeline = [
        {"$match": {"exchange_id": exchange_id, "commission_date": {"$gte": start, "$lte": end}}},
        {
            "$group": {
                "_id": None,
                "total_volume": {"$sum": "$trading_volume"},
                "total_commission": {"$sum": "$commission_volume"},
                "uids": {"$addToSet": "$user_id"},
            }
        },
        {"$project": {"total_volume": 1, "total_commission": 1, "total_users": {"$size": "$uids"}}},
    ]
    rows = await dc_collection.aggregate(pipeline).to_list(length=1)
    if not rows:
        return {
            "total_deposit": 0,
            "total_volume": 0,
            "total_commission": 0,
            "total_users": 0,
            "active_users": 0,
        }
    r = rows[0]
    n = r["total_users"]
    return {
        "total_deposit": 0,
        "total_volume": r["total_volume"],
        "total_commission": r["total_commission"],
        "total_users": n,
        "active_users": n,
    }


async def _exchange_stats_from_referred_registered(start: datetime, end: datetime, exchange_id: str) -> Dict[str, Any]:
    collection = ReferredUser.get_motor_collection()
    pipeline = [
        {"$match": {"exchange_id": exchange_id, "registered_at": {"$gte": start, "$lte": end}}},
        {
            "$group": {
                "_id": None,
                "total_deposit": {"$sum": "$total_deposit"},
                "total_volume": {"$sum": "$total_volume"},
                "total_commission": {"$sum": "$total_commission"},
                "total_users": {"$sum": 1},
                "active_users": {"$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}},
            }
        },
    ]
    rows = await collection.aggregate(pipeline).to_list(length=1)
    if not rows:
        return {
            "total_deposit": 0,
            "total_volume": 0,
            "total_commission": 0,
            "total_users": 0,
            "active_users": 0,
        }
    row = rows[0]
    return {
        "total_deposit": row["total_deposit"],
        "total_volume": row["total_volume"],
        "total_commission": row["total_commission"],
        "total_users": row["total_users"],
        "active_users": row["active_users"],
    }


@router.get("/{exchange_id}")
async def exchange_stats(
    exchange_id: str,
    _: CurrentAdmin,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    bounds = _validate_range_params(from_date, to_date)
    if bounds is None:
        return await _exchange_stats_all_time(exchange_id)

    start, end = bounds
    dc_collection = DailyCommission.get_motor_collection()
    dc_count = await dc_collection.count_documents(
        {"exchange_id": exchange_id, "commission_date": {"$gte": start, "$lte": end}}
    )
    if dc_count > 0:
        return await _exchange_stats_from_daily(start, end, exchange_id)
    return await _exchange_stats_from_referred_registered(start, end, exchange_id)
