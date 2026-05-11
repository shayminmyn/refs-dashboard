"""
Bitget — Affiliate (Agent) & Broker API v2
Tài liệu tham chiếu: https://www.bitget.com/api-doc/affiliate/intro

Dữ liệu referral + commission daily dùng các endpoint Agent (affiliate customer):
  POST /api/v2/broker/customer-list          — danh sách khách (uid, registerTime)
  GET  /api/v2/broker/customer-commissions — chi tiết rebate/hoa hồng theo ngày (uid, date, …)

Chữ ký REST v2 (Bitget):
  prehash = timestamp + METHOD + requestPath + ("?" + queryString nếu GET có query) + body

Biến môi trường: BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE, BITGET_BASE_URL
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import random
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.adapters.base import BaseExchangeAdapter, GenericDailyCommission, NormalizedUser
from app.config import settings

logger = logging.getLogger(__name__)

SUCCESS_CODE = "00000"
CUSTOMER_LIST_PATH = "/api/v2/broker/customer-list"
CUSTOMER_COMMISSIONS_PATH = "/api/v2/broker/customer-commissions"


def _float_bitget(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _parse_bitget_date(raw: str) -> date:
    """Field `date` từ API — có thể là ms hoặc YYYY-MM-DD."""
    if not raw:
        return date.today()
    raw = str(raw).strip()
    if raw.isdigit():
        ms = int(raw)
        # Heuristic: > 1e12 → milliseconds
        if ms > 1_000_000_000_000:
            return datetime.utcfromtimestamp(ms / 1000).date()
        if ms > 1_000_000_000:
            return datetime.utcfromtimestamp(ms).date()
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return date.today()


class BitgetAdapter(BaseExchangeAdapter):
    @property
    def exchange_id(self) -> str:
        return "bitget"

    def _sign(self, timestamp: str, method: str, path: str, query_string: str, body: str) -> str:
        """
        Bitget v2: timestamp + METHOD + requestPath + (?queryString) + body
        """
        method = method.upper()
        if query_string:
            pre = f"{timestamp}{method}{path}?{query_string}{body}"
        else:
            pre = f"{timestamp}{method}{path}{body}"
        mac = hmac.new(settings.bitget_api_secret.encode(), pre.encode(), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode()

    def _headers(self, timestamp: str, signature: str) -> Dict[str, str]:
        return {
            "ACCESS-KEY": settings.bitget_api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": settings.bitget_api_passphrase,
            "Content-Type": "application/json",
            "locale": "en-US",
        }

    def _build_query_string(self, params: Dict[str, Any]) -> str:
        if not params:
            return ""
        # Alphabetical keys — khớp convention Bitget sample
        parts = [f"{k}={params[k]}" for k in sorted(params.keys()) if params[k] is not None]
        return "&".join(parts)

    async def _get_private(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        qs = self._build_query_string(params or {})
        timestamp = str(int(time.time() * 1000))
        sig = self._sign(timestamp, "GET", path, qs, "")
        url = f"{settings.bitget_base_url.rstrip('/')}{path}"
        if qs:
            url = f"{url}?{qs}"
        resp = await client.get(url, headers=self._headers(timestamp, sig), timeout=30.0)
        resp.raise_for_status()
        return self._unwrap(resp.json())

    async def _post_private(
        self,
        client: httpx.AsyncClient,
        path: str,
        body: Dict[str, Any],
    ) -> Any:
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
        timestamp = str(int(time.time() * 1000))
        sig = self._sign(timestamp, "POST", path, "", body_str)
        url = f"{settings.bitget_base_url.rstrip('/')}{path}"
        resp = await client.post(
            url,
            headers=self._headers(timestamp, sig),
            content=body_str.encode("utf-8"),
            timeout=30.0,
        )
        resp.raise_for_status()
        return self._unwrap(resp.json())

    def _unwrap(self, payload: Dict[str, Any]) -> Any:
        code = str(payload.get("code", ""))
        if code != SUCCESS_CODE:
            raise RuntimeError(f"Bitget API lỗi [{code}]: {payload.get('msg')}")
        return payload.get("data")

    async def _fetch_agent_customer_list_all(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """POST customer-list — phân trang pageNo/pageSize."""
        all_rows: List[Dict[str, Any]] = []
        page_no = 1
        page_size = 100
        while True:
            body = {"pageNo": str(page_no), "pageSize": str(page_size)}
            data = await self._post_private(client, CUSTOMER_LIST_PATH, body)
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = data.get("list") or data.get("customerList") or []
            else:
                rows = []
            if not rows:
                break
            all_rows.extend(rows)
            if len(rows) < page_size:
                break
            page_no += 1
            if page_no > 500:
                logger.warning("[Bitget] customer-list: dừng sau 500 trang")
                break
        return all_rows

    async def _fetch_customer_commissions_window(
        self,
        client: httpx.AsyncClient,
        start_ms: int,
        end_ms: int,
    ) -> List[Dict[str, Any]]:
        """
        GET customer-commissions — cursor idLessThan = endId.
        """
        collected: List[Dict[str, Any]] = []
        id_less_than: Optional[str] = None
        limit = "100"

        for _ in range(1000):
            params: Dict[str, Any] = {
                "startTime": str(start_ms),
                "endTime": str(end_ms),
                "limit": limit,
            }
            if id_less_than:
                params["idLessThan"] = id_less_than

            data = await self._get_private(client, CUSTOMER_COMMISSIONS_PATH, params)
            if not isinstance(data, dict):
                break
            chunk = data.get("commissionList") or []
            if not chunk:
                break
            collected.extend(chunk)
            end_id = data.get("endId")
            if not end_id:
                break
            id_less_than = str(end_id)
            if len(chunk) < int(limit):
                break

        return collected

    async def fetch_referrals(self, commission_days: int = 30) -> List[NormalizedUser]:
        if not settings.bitget_api_key or not settings.bitget_api_secret:
            logger.warning("[Bitget] Chưa cấu hình API — dùng dữ liệu mock")
            return self._mock_data()

        now_ms = int(time.time() * 1000)
        start_ms = now_ms - commission_days * 24 * 3600 * 1000

        try:
            async with httpx.AsyncClient() as client:
                rows = await self._fetch_agent_customer_list_all(client)
                comm_rows = await self._fetch_customer_commissions_window(
                    client, start_ms, now_ms
                )

                vol_comm: Dict[str, Dict[str, float]] = defaultdict(
                    lambda: {"volume": 0.0, "commission": 0.0}
                )
                for r in comm_rows:
                    uid = str(r.get("uid") or "")
                    if not uid:
                        continue
                    vol_comm[uid]["volume"] += _float_bitget(r.get("dealAmount"))
                    vol_comm[uid]["commission"] += _float_bitget(r.get("rebateAmount"))

                users: List[NormalizedUser] = []
                for row in rows:
                    uid = str(row.get("uid") or "")
                    if not uid:
                        continue
                    reg_raw = row.get("registerTime")
                    registered_at = datetime.utcnow()
                    if reg_raw:
                        try:
                            ms = int(str(reg_raw))
                            registered_at = datetime.utcfromtimestamp(ms / 1000)
                        except (ValueError, TypeError):
                            pass
                    agg = vol_comm.get(uid, {"volume": 0.0, "commission": 0.0})
                    vol = agg["volume"]
                    users.append(
                        NormalizedUser(
                            user_id=uid,
                            username=uid,
                            email="",
                            registered_at=registered_at,
                            total_deposit=0.0,
                            total_volume=vol,
                            total_commission=agg["commission"],
                            status="active" if vol > 0 else "inactive",
                            raw_data=row,
                        )
                    )
                logger.info("[Bitget] fetch_referrals: %d users, %d commission rows", len(users), len(comm_rows))
                return users

        except Exception as exc:
            logger.error("[Bitget] fetch_referrals lỗi: %s", exc)
            raise

    async def fetch_daily_commissions_raw(self, days_back: int = 30) -> List[GenericDailyCommission]:
        if not settings.bitget_api_key or not settings.bitget_api_secret:
            return []

        now_ms = int(time.time() * 1000)
        start_ms = now_ms - days_back * 24 * 3600 * 1000

        # Gom (uid, commission_date) — có thể nhiều symbol/coin trong một ngày
        agg: Dict[Tuple[str, date], Dict[str, float]] = defaultdict(
            lambda: {"trading_volume": 0.0, "commission_volume": 0.0}
        )

        async with httpx.AsyncClient() as client:
            rows = await self._fetch_customer_commissions_window(client, start_ms, now_ms)

        for r in rows:
            uid = str(r.get("uid") or "")
            if not uid:
                continue
            d = _parse_bitget_date(str(r.get("date") or ""))
            key = (uid, d)
            agg[key]["trading_volume"] += _float_bitget(r.get("dealAmount"))
            agg[key]["commission_volume"] += _float_bitget(r.get("rebateAmount"))

        result = [
            GenericDailyCommission(
                uid=k[0],
                commission_date=k[1],
                trading_volume=v["trading_volume"],
                commission_volume=v["commission_volume"],
            )
            for k, v in agg.items()
        ]
        logger.info("[Bitget] fetch_daily_commissions_raw: %d bản ghi (window %d ngày)", len(result), days_back)
        return result

    def _mock_data(self) -> List[NormalizedUser]:
        return [
            NormalizedUser(
                user_id=f"bg_user_{i + 1}",
                username=f"bitget_trader_{i + 1}",
                email=f"trader{i + 1}@bitget-demo.com",
                registered_at=datetime.utcnow() - timedelta(days=i * 5),
                total_deposit=round(random.uniform(200, 8000), 2),
                total_volume=round(random.uniform(2000, 300000), 2),
                total_commission=round(random.uniform(10, 800), 2),
                status="inactive" if i % 5 == 0 else "active",
                raw_data={"source": "mock"},
            )
            for i in range(5)
        ]
