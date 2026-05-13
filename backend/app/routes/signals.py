"""
API đọc performance signals từ MongoDB trading.signals (read-only).
"""

from datetime import datetime, timezone
from typing import Literal, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.middleware.auth import CurrentAdmin
from app.services import trading_signals as ts

router = APIRouter(prefix="/api/signals", tags=["signals"])


def _signals_coll(request: Request):
    return request.app.state.trading_mongo_client[settings.trading_db_name][
        settings.trading_signals_collection
    ]


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


def _validate_range_params(
    from_date: Optional[str], to_date: Optional[str]
) -> Optional[Tuple[datetime, datetime]]:
    if from_date is None and to_date is None:
        return None
    if from_date is None or to_date is None:
        raise HTTPException(
            status_code=400,
            detail="Gửi cả query from và to (YYYY-MM-DD), hoặc bỏ cả hai (toàn thời gian).",
        )
    return _parse_date_bounds(from_date, to_date)


def _build_match(
    from_date: Optional[str],
    to_date: Optional[str],
    symbol: Optional[str],
    strategy: Optional[str],
    timeframe: Optional[str],
    status: Optional[str],
):
    base = ts.build_base_match(symbol, strategy, timeframe, status)
    bounds = _validate_range_params(from_date, to_date)
    if bounds is None:
        return base
    date_part = ts.build_date_match(bounds[0], bounds[1])
    return ts.merge_match(base, date_part)


@router.get("")
async def list_signals(
    _: CurrentAdmin,
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    symbol: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    sort_dir: Literal["asc", "desc"] = Query("desc", alias="sortDir"),
):
    coll = _signals_coll(request)
    match = _build_match(from_date, to_date, symbol, strategy, timeframe, status)
    rows, total = await ts.list_signals_page(coll, match, page, limit, sort_dir)
    return {
        "data": rows,
        "pagination": ts.pagination_meta(page, limit, total),
    }


@router.get("/stats")
async def signals_stats(
    _: CurrentAdmin,
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    symbol: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    timeframe: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    coll = _signals_coll(request)
    match = _build_match(from_date, to_date, symbol, strategy, timeframe, status)
    stats = await ts.aggregate_stats(coll, match)
    return stats


@router.get("/filters")
async def signals_filters(
    _: CurrentAdmin,
    request: Request,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    """Distinct symbol / strategy / timeframe trong range (hoặc toàn bộ)."""
    coll = _signals_coll(request)
    bounds = _validate_range_params(from_date, to_date)
    date_part = ts.build_date_match(bounds[0], bounds[1]) if bounds else None
    match = ts.merge_match({}, date_part) if date_part else {}
    symbols = await ts.distinct_union(coll, match, ts.SYMBOL_KEYS)
    strategies = await ts.distinct_union(coll, match, ts.STRATEGY_KEYS)
    timeframes = await ts.distinct_union(coll, match, ts.TIMEFRAME_KEYS)
    statuses = await ts.distinct_union(coll, match, ts.STATUS_KEYS)
    return {
        "symbols": symbols,
        "strategies": strategies,
        "timeframes": timeframes,
        "statuses": statuses,
    }
