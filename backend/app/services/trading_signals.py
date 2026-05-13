"""
Đọc collection signals trong DB trading — field names linh hoạt (alias).
"""

from datetime import datetime, timezone
from math import ceil
from typing import Any, Dict, List, Optional, Sequence, Tuple

from bson import ObjectId
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorCollection

from app.config import settings


def _split_csv(s: str) -> List[str]:
    return [p.strip() for p in s.split(",") if p.strip()]


def _date_fields() -> List[str]:
    xs = _split_csv(settings.signal_filter_date_fields)
    return xs if xs else ["closed_at"]


SYMBOL_KEYS = ("symbol", "pair", "instrument")
STRATEGY_KEYS = ("strategy", "strategy_name", "strategyName")
TIMEFRAME_KEYS = ("timeframe", "tf", "time_frame", "timeFrame")
STATUS_KEYS = ("status", "state", "order_status", "orderStatus", "signal_status", "signalStatus", "paper_status", "paperStatus")
RR_KEYS = ("rr_ratio", "rrRatio", "risk_reward", "riskReward")
RISK_PERCENT_KEYS = (
    "risk_percent",
    "riskPercent",
    "risk_pct",
    "riskPct",
    "account_risk_percent",
    "accountRiskPercent",
    "risk_per_trade_percent",
    "riskPerTradePercent",
)
REALIZED_R_KEYS = (
    "realized_r",
    "realizedR",
    "r_multiple",
    "profit_r",
    "net_r",
    "profit_in_r",
    "profitInR",
    "r_result",
    "rResult",
)
OUTCOME_KEYS = ("exit_reason", "exitReason", "close_reason", "closeReason", "outcome", "result")

# Alias schema signals — ưu tiên đầu tuple khi đọc/ghi response API
ORDER_TYPE_KEYS = ("action", "order_type", "orderType", "type", "side")
ENTRY_PRICE_KEYS = ("entry", "entry_price", "entryPrice", "price")
CLOSED_AT_KEYS = (
    "time_exit",
    "timeExit",
    "time_closed",
    "timeClosed",
    "time_resolved",
    "timeResolved",
    "time_signal_closed",
    "timeSignalClosed",
    "time_updated",
    "timeUpdated",
    "time_signal_at",
    "timeSignalAt",
    "time_created",
    "timeCreated",
)
def pick_str(doc: Dict[str, Any], keys: Sequence[str]) -> Optional[str]:
    for k in keys:
        v = doc.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def coerce_float(v: Any) -> Optional[float]:
    """Mongo hay lưu RR/R bằng Decimal128 — float() trực tiếp sẽ lỗi / bỏ qua."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, Decimal128):
        return float(v.to_decimal())
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pick_float(doc: Dict[str, Any], keys: Sequence[str]) -> Optional[float]:
    for k in keys:
        v = doc.get(k)
        if v is None:
            continue
        f = coerce_float(v)
        if f is not None:
            return f
    return None


def pick_dt(doc: Dict[str, Any], keys: Sequence[str]) -> Optional[datetime]:
    for k in keys:
        v = doc.get(k)
        if isinstance(v, datetime):
            return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
        # Extended JSON / dump lạ
        if isinstance(v, dict) and "$date" in v:
            inner = v["$date"]
            if isinstance(inner, (int, float)):
                sec = inner / 1000.0 if inner > 1e12 else float(inner)
                return datetime.fromtimestamp(sec, tz=timezone.utc)
            if isinstance(inner, str):
                try:
                    raw = inner.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(raw)
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
        if isinstance(v, str):
            s = v.strip()
            if s:
                try:
                    raw = s.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(raw)
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    pass
        # Một số schema lưu thời điểm đóng tại `tp` dạng unix (s hoặc ms)
        if k == "tp" and isinstance(v, (int, float)):
            fv = float(v)
            if fv > 1e9:
                ts = fv / 1000.0 if fv > 1e12 else fv
                return datetime.fromtimestamp(ts, tz=timezone.utc)
    return None


def is_closed_trade(doc: Dict[str, Any]) -> bool:
    st = pick_str(doc, STATUS_KEYS)
    if not st:
        return False
    return st.strip().upper() == "CLOSED"


def risk_pct_per_r_multiplier(raw: Optional[float]) -> Optional[float]:
    """
    Chuẩn hoá risk → '% equity / 1R' để cộng dồn P&L %: Δ% ≈ multiplier * realized_r.
    - 1.5 hoặc 2 → hiểu là 1.5%, 2% mỗi 1R.
    - 0 < x < 1 → hiểu là phần thập phân (0.015 → 1.5%).
    """
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    if 0 < v < 1:
        return v * 100.0
    return v


def realized_r_value(doc: Dict[str, Any]) -> Optional[float]:
    r = pick_float(doc, REALIZED_R_KEYS)
    if r is not None:
        return r
    outcome = pick_str(doc, OUTCOME_KEYS)
    rr = pick_float(doc, RR_KEYS)
    if outcome:
        o = outcome.lower()
        if o in ("tp", "take_profit", "takeprofit"):
            return rr if rr is not None else 1.0
        if o in ("sl", "stop_loss", "stoploss", "stop"):
            return -1.0
        if o in ("expired", "cancelled", "canceled", "be", "breakeven"):
            return 0.0
    return None


def equality_or(keys: Sequence[str], value: str) -> Dict[str, Any]:
    if len(keys) == 1:
        return {keys[0]: value}
    return {"$or": [{k: value} for k in keys]}


def build_base_match(
    symbol: Optional[str],
    strategy: Optional[str],
    timeframe: Optional[str],
    status: Optional[str],
) -> Dict[str, Any]:
    parts: List[Dict[str, Any]] = []
    if symbol:
        parts.append(equality_or(SYMBOL_KEYS, symbol))
    if strategy:
        parts.append(equality_or(STRATEGY_KEYS, strategy))
    if timeframe:
        parts.append(equality_or(TIMEFRAME_KEYS, timeframe))
    if status:
        parts.append(equality_or(STATUS_KEYS, status))
    if not parts:
        return {}
    if len(parts) == 1:
        return parts[0]
    return {"$and": parts}


def _iso_utc_z(dt: datetime) -> str:
    """ISO8601 UTC có ms — so sánh lexicographic khớp nhiều dump string trong Mongo."""
    utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    base = utc.strftime("%Y-%m-%dT%H:%M:%S")
    ms = utc.microsecond // 1000
    return f"{base}.{ms:03d}Z"


def build_date_match(from_dt: datetime, to_dt: datetime) -> Dict[str, Any]:
    """Một field có thể là BSON Date hoặc string ISO — OR hai nhánh cho mỗi tên field."""
    fields = list(_date_fields())
    from_s = _iso_utc_z(from_dt)
    to_s = _iso_utc_z(to_dt)
    branches: List[Dict[str, Any]] = []
    for fn in fields:
        branches.append({fn: {"$gte": from_dt, "$lte": to_dt}})
        branches.append({fn: {"$gte": from_s, "$lte": to_s}})
    if len(branches) == 1:
        return branches[0]
    return {"$or": branches}


def merge_match(base: Dict[str, Any], date_part: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not date_part:
        return dict(base)
    if not base:
        return dict(date_part)
    return {"$and": [base, date_part]}


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    oid = doc.get("_id")
    row_id = str(oid) if isinstance(oid, ObjectId) else str(oid) if oid is not None else ""

    order_type = pick_str(doc, ORDER_TYPE_KEYS)
    sym = pick_str(doc, SYMBOL_KEYS)
    strat = pick_str(doc, STRATEGY_KEYS)
    tf = pick_str(doc, TIMEFRAME_KEYS)
    st = pick_str(doc, STATUS_KEYS)
    signal_key = pick_str(doc, ("signal_key", "signalKey", "signal_id", "idempotency_key"))
    comment = pick_str(doc, ("comment", "message", "notes", "description"))
    outcome = pick_str(doc, OUTCOME_KEYS)

    r = realized_r_value(doc)
    rr = pick_float(doc, RR_KEYS)
    risk_raw = pick_float(doc, RISK_PERCENT_KEYS)

    return {
        "_id": row_id,
        "order_type": order_type,
        "symbol": sym,
        "strategy": strat,
        "timeframe": tf,
        "status": st,
        "signal_key": signal_key,
        "comment": comment,
        "exit_reason": outcome,
        "rr_ratio": rr,
        "risk_percent": risk_raw,
        "realized_r": r,
        "closed_at": pick_dt(doc, CLOSED_AT_KEYS),
        "signal_at": pick_dt(doc, ("signal_at", "signalAt", "opened_at", "open_time")),
        "entry_price": pick_float(doc, ENTRY_PRICE_KEYS),
        "stop_loss": pick_float(doc, ("stop_loss", "stopLoss", "sl")),
        "is_closed": is_closed_trade(doc),
    }


async def aggregate_stats(coll: AsyncIOMotorCollection, match: Dict[str, Any]) -> Dict[str, Any]:
    cursor = coll.find(match)
    total_rows = 0
    closed_trades = 0
    wins = 0
    losses = 0
    breakeven = 0
    unsettled = 0
    total_r = 0.0
    total_return_pct = 0.0
    total_target_rr_pct = 0.0
    trades_with_risk = 0

    async for raw in cursor:
        doc = dict(raw)
        total_rows += 1
        if not is_closed_trade(doc):
            continue
        r = realized_r_value(doc)
        if r is None:
            unsettled += 1
            continue
        closed_trades += 1
        total_r += r
        if r > 0:
            wins += 1
        elif r < 0:
            losses += 1
        else:
            breakeven += 1

        risk_m = risk_pct_per_r_multiplier(pick_float(doc, RISK_PERCENT_KEYS))
        if risk_m is not None:
            trades_with_risk += 1
            total_return_pct += risk_m * r
            rr = pick_float(doc, RR_KEYS)
            if rr is not None:
                total_target_rr_pct += risk_m * rr

    denom = wins + losses
    win_rate = (wins / denom) if denom else None
    avg_r = (total_r / closed_trades) if closed_trades else None
    avg_return_pct = (total_return_pct / trades_with_risk) if trades_with_risk else None

    return {
        "total_signals": total_rows,
        "closed_trades": closed_trades,
        "wins": wins,
        "losses": losses,
        "breakeven": breakeven,
        "unsettled_r": unsettled,
        "win_rate": win_rate,
        "total_r": round(total_r, 6),
        "avg_r": round(avg_r, 6) if avg_r is not None else None,
        "total_return_pct": round(total_return_pct, 6),
        "total_target_rr_pct": round(total_target_rr_pct, 6),
        "trades_with_risk_pct": trades_with_risk,
        "avg_return_pct": round(avg_return_pct, 6) if avg_return_pct is not None else None,
    }


async def list_signals_page(
    coll: AsyncIOMotorCollection,
    match: Dict[str, Any],
    page: int,
    limit: int,
    sort_dir: str,
) -> Tuple[List[Dict[str, Any]], int]:
    skip = (page - 1) * limit
    sort_order = 1 if sort_dir == "asc" else -1
    sort_spec = [(f, sort_order) for f in _date_fields()]

    total = await coll.count_documents(match)
    cursor = coll.find(match).sort(sort_spec).skip(skip).limit(limit)
    rows: List[Dict[str, Any]] = []
    async for raw in cursor:
        rows.append(serialize_doc(dict(raw)))

    return rows, total


def pagination_meta(page: int, limit: int, total: int) -> Dict[str, Any]:
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": ceil(total / limit) if limit else 0,
    }


async def distinct_union(
    coll: AsyncIOMotorCollection,
    match: Dict[str, Any],
    keys: Sequence[str],
    limit: int = 500,
) -> List[str]:
    found: set[str] = set()
    for k in keys:
        vals = await coll.distinct(k, filter=match if match else None)
        for v in vals:
            if v is None:
                continue
            s = str(v).strip()
            if s:
                found.add(s)
            if len(found) >= limit:
                return sorted(found)[:limit]
    return sorted(found)
