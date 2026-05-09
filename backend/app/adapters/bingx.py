"""
BingX Agent API Adapter
Tài liệu: https://bingx-api.github.io/docs-v3/#/en/agent

Các endpoint sử dụng:
  GET /openApi/agent/v1/account/inviteAccountList   — danh sách user được mời
  GET /openApi/agent/v2/reward/commissionDataList   — hoa hồng hàng ngày
  GET /openApi/agent/v1/account/inviteRelationCheck — thông tin chi tiết 1 user

Xác thực: HMAC-SHA256, header X-BX-APIKEY + query param signature
"""

import hashlib
import hmac
import logging
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.adapters.base import BaseExchangeAdapter, NormalizedUser
from app.config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Internal dataclass cho dữ liệu thô từ BingX
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class BingXUserInfo:
    uid: int
    registered_at: datetime
    deposit: bool           # đã nạp tiền chưa
    trade: bool             # đã giao dịch chưa
    balance_volume: float   # tài sản ròng (USDT)
    commission_ratio: int   # tỷ lệ hoa hồng (%)
    direct: bool            # mời trực tiếp
    kyc: str


@dataclass
class BingXDailyCommission:
    uid: int
    commission_date: date
    trading_volume: float
    commission_volume: float
    spot_volume: float
    spot_commission: float
    swap_volume: float
    swap_commission: float
    std_volume: float
    std_commission: float
    copy_volume: float
    copy_commission: float


# ──────────────────────────────────────────────────────────────────────────────
# Adapter chính
# ──────────────────────────────────────────────────────────────────────────────

class BingXAdapter(BaseExchangeAdapter):

    @property
    def exchange_id(self) -> str:
        return "bingx"

    # ── Ký request ────────────────────────────────────────────────────────────

    def _build_query_and_sign(self, extra: Dict[str, Any]) -> Tuple[str, str]:
        """
        Xây dựng query string và chữ ký theo đúng spec BingX:
        - Sắp xếp các param khác theo alphabet
        - Timestamp đặt ở cuối (BingX sample code yêu cầu)
        - Không dùng urlencode để tránh percent-encoding không mong muốn
        """
        ts = int(time.time() * 1000)
        sorted_parts = "&".join(
            f"{k}={v}" for k, v in sorted(extra.items())
        )
        query_to_sign = f"{sorted_parts}&timestamp={ts}" if sorted_parts else f"timestamp={ts}"

        signature = hmac.new(
            settings.bingx_api_secret.encode("utf-8"),
            query_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return query_to_sign, signature

    async def _get(self, client: httpx.AsyncClient, path: str, extra: Dict[str, Any]) -> Any:
        """Gửi GET request đã ký đến BingX API."""
        query_str, signature = self._build_query_and_sign(extra)
        full_url = f"{settings.bingx_base_url}{path}?{query_str}&signature={signature}"
        resp = await client.get(
            full_url,
            headers={"X-BX-APIKEY": settings.bingx_api_key},
            timeout=20,
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("code", 0) != 0:
            raise RuntimeError(f"BingX API lỗi [{body.get('code')}]: {body.get('msg')}")
        return body.get("data", {})

    # ── Lấy danh sách user được mời (có phân trang) ───────────────────────────

    async def _fetch_all_invited_users(self, client: httpx.AsyncClient) -> List[BingXUserInfo]:
        """
        GET /openApi/agent/v1/account/inviteAccountList
        Params: pageIndex, pageSize (max 100), startTime, endTime, lastUid
        Response: { total, dataList: [...] }
        """
        users: List[BingXUserInfo] = []
        page = 1
        page_size = 100
        last_uid: Optional[int] = None

        while True:
            extra: Dict[str, Any] = {"pageIndex": page, "pageSize": page_size}
            if last_uid is not None:
                extra["lastUid"] = last_uid

            data = await self._get(client, "/openApi/agent/v1/account/inviteAccountList", extra)
            rows: List[Dict[str, Any]] = data.get("dataList") or data.get("list") or []

            if not rows:
                break

            for row in rows:
                reg_ms = row.get("registerDateTime") or row.get("registerTime") or 0
                users.append(BingXUserInfo(
                    uid=int(row.get("uid", 0)),
                    registered_at=datetime.utcfromtimestamp(int(reg_ms) / 1000) if reg_ms else datetime.utcnow(),
                    deposit=bool(row.get("deposit", False)),
                    trade=bool(row.get("trade", False)),
                    balance_volume=float(row.get("balanceVolume") or 0),
                    commission_ratio=int(row.get("commissionRatio") or 0),
                    direct=bool(row.get("directInvitation", True)),
                    kyc=str(row.get("kycResult") or ""),
                ))
                last_uid = int(row.get("uid", 0))

            total = int(data.get("total") or data.get("totalCount") or 0)
            if len(users) >= total or len(rows) < page_size:
                break

            page += 1

        return users

    # ── Lấy hoa hồng hàng ngày ────────────────────────────────────────────────

    async def _fetch_commission_window(
        self,
        client: httpx.AsyncClient,
        start_ms: int,
        end_ms: int,
    ) -> List[BingXDailyCommission]:
        """
        Lấy hoa hồng cho một window thời gian (tối đa 7 ngày).
        GET /openApi/agent/v2/reward/commissionDataList
        """
        entries: List[BingXDailyCommission] = []
        page = 1
        page_size = 100

        while True:
            extra: Dict[str, Any] = {
                "startTime": start_ms,
                "endTime": end_ms,
                "pageIndex": page,
                "pageSize": page_size,
            }
            data = await self._get(client, "/openApi/agent/v2/reward/commissionDataList", extra)
            rows: List[Dict[str, Any]] = data.get("dataList") or data.get("list") or []

            if not rows:
                break

            for row in rows:
                ts_ms = int(row.get("commissionTime") or 0)
                comm_date = (
                    datetime.utcfromtimestamp(ts_ms / 1000).date()
                    if ts_ms else date.today()
                )
                entries.append(BingXDailyCommission(
                    uid=int(row.get("uid", 0)),
                    commission_date=comm_date,
                    trading_volume=float(row.get("tradingVolume") or 0),
                    commission_volume=float(row.get("commissionVolume") or 0),
                    spot_volume=float(row.get("spotTradingVolume") or 0),
                    spot_commission=float(row.get("spotCommissionVolume") or 0),
                    swap_volume=float(row.get("swapTradingVolume") or 0),
                    swap_commission=float(row.get("swapCommissionVolume") or 0),
                    std_volume=float(row.get("stdTradingVolume") or 0),
                    std_commission=float(row.get("stdCommissionVolume") or 0),
                    copy_volume=float(row.get("extCopyTradingVolume") or 0),
                    copy_commission=float(row.get("extCopyCommissionVolume") or 0),
                ))

            total = int(data.get("total") or data.get("totalCount") or 0)
            if len(entries) >= total or len(rows) < page_size:
                break

            page += 1

        return entries

    async def _fetch_daily_commissions(
        self,
        client: httpx.AsyncClient,
        start_ms: int,
        end_ms: int,
    ) -> List[BingXDailyCommission]:
        """
        BingX giới hạn mỗi request tối đa 7 ngày (daysRange-over-7).
        Chia toàn bộ range thành các window 6 ngày và gộp kết quả.
        """
        WINDOW_MS = 6 * 24 * 3600 * 1000  # 6 ngày (an toàn hơn 7)
        all_entries: List[BingXDailyCommission] = []

        window_start = start_ms
        while window_start < end_ms:
            window_end = min(window_start + WINDOW_MS, end_ms)
            chunk = await self._fetch_commission_window(client, window_start, window_end)
            all_entries.extend(chunk)
            logger.debug(
                "[BingX] Commission window %s → %s: %d bản ghi",
                datetime.utcfromtimestamp(window_start / 1000).date(),
                datetime.utcfromtimestamp(window_end / 1000).date(),
                len(chunk),
            )
            window_start = window_end + 1  # tránh overlap

        return all_entries

    # ── Public: fetch_referrals ────────────────────────────────────────────────

    async def fetch_referrals(self, commission_days: int = 30) -> List[NormalizedUser]:
        """
        Lấy danh sách người dùng + tổng hợp hoa hồng.
        commission_days: số ngày hoa hồng để tính total_volume / total_commission cho user.
        """
        if not settings.bingx_api_key or not settings.bingx_api_secret:
            logger.warning("[BingX] Chưa cấu hình API key — dùng dữ liệu mock")
            return self._mock_data()

        try:
            async with httpx.AsyncClient() as client:
                # 1. Lấy danh sách người dùng
                users = await self._fetch_all_invited_users(client)
                logger.info("[BingX] Lấy được %d người dùng được mời", len(users))

                if not users:
                    return []

                # 2. Lấy hoa hồng theo commission_days (chia window 6 ngày)
                now_ms = int(time.time() * 1000)
                start_ms = now_ms - commission_days * 24 * 3600 * 1000
                commissions = await self._fetch_daily_commissions(client, start_ms, now_ms)
                logger.info("[BingX] Lấy được %d bản ghi hoa hồng (%d ngày)", len(commissions), commission_days)

                # 3. Tổng hợp hoa hồng theo uid
                commission_by_uid: Dict[int, Dict[str, float]] = defaultdict(
                    lambda: {"total_volume": 0.0, "total_commission": 0.0}
                )
                for c in commissions:
                    commission_by_uid[c.uid]["total_volume"] += c.trading_volume
                    commission_by_uid[c.uid]["total_commission"] += c.commission_volume

                # 4. Chuẩn hoá
                result: List[NormalizedUser] = []
                for u in users:
                    agg = commission_by_uid.get(u.uid, {})
                    result.append(NormalizedUser(
                        user_id=str(u.uid),
                        username=f"uid_{u.uid}",
                        email="",
                        registered_at=u.registered_at,
                        total_deposit=u.balance_volume,   # dùng balance_volume như proxy deposit
                        total_volume=agg.get("total_volume", 0.0),
                        total_commission=agg.get("total_commission", 0.0),
                        status="active" if u.trade else "inactive",
                        raw_data={
                            "uid": u.uid,
                            "deposit": u.deposit,
                            "trade": u.trade,
                            "balance_volume": u.balance_volume,
                            "commission_ratio": u.commission_ratio,
                            "direct": u.direct,
                            "kyc": u.kyc,
                        },
                    ))

                return result

        except Exception as exc:
            logger.error("[BingX] fetch_referrals lỗi: %s", exc)
            raise

    # ── Public: fetch_daily_commissions (dùng bởi sync_service) ──────────────

    async def fetch_daily_commissions_raw(
        self,
        days_back: int = 30,
    ) -> List[BingXDailyCommission]:
        """
        Lấy dữ liệu hoa hồng thô để lưu vào DailyCommission collection.
        Mặc định 30 ngày, tự động chia thành các window 6 ngày.
        """
        if not settings.bingx_api_key or not settings.bingx_api_secret:
            return self._mock_commissions(days_back)

        now_ms = int(time.time() * 1000)
        start_ms = now_ms - days_back * 24 * 3600 * 1000

        async with httpx.AsyncClient() as client:
            return await self._fetch_daily_commissions(client, start_ms, now_ms)

    # ── Mock data ─────────────────────────────────────────────────────────────

    def _mock_data(self) -> List[NormalizedUser]:
        return [
            NormalizedUser(
                user_id=f"bx_{10000 + i}",
                username=f"uid_{10000 + i}",
                email="",
                registered_at=datetime.utcnow() - timedelta(days=i * 7),
                total_deposit=round(random.uniform(100, 5000), 2),
                total_volume=round(random.uniform(1000, 200000), 2),
                total_commission=round(random.uniform(5, 500), 2),
                status="inactive" if i % 3 == 0 else "active",
                raw_data={"uid": 10000 + i, "deposit": True, "trade": i % 3 != 0, "source": "mock"},
            )
            for i in range(8)
        ]

    def _mock_commissions(self, days_back: int) -> List[BingXDailyCommission]:
        entries = []
        uids = [10001, 10002, 10003, 10004]
        for uid in uids:
            for d in range(min(days_back, 30)):
                vol = round(random.uniform(500, 10000), 2)
                comm = round(vol * random.uniform(0.001, 0.005), 4)
                entries.append(BingXDailyCommission(
                    uid=uid,
                    commission_date=date.today() - timedelta(days=d),
                    trading_volume=vol,
                    commission_volume=comm,
                    spot_volume=vol * 0.4,
                    spot_commission=comm * 0.4,
                    swap_volume=vol * 0.6,
                    swap_commission=comm * 0.6,
                    std_volume=0,
                    std_commission=0,
                    copy_volume=0,
                    copy_commission=0,
                ))
        return entries
