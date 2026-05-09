"""
Exness Partnership API Adapter
Tài liệu: https://my.exnessaffiliates.com/api/schema/

Xác thực: JWT — đăng nhập bằng email + password, nhận token JWT.
Header: Authorization: JWT <token>

Các endpoint sử dụng:
  POST /api/v2/auth/                   — lấy JWT token
  GET  /api/v2/reports/clients/        — danh sách client (phân trang, filter theo ngày)
  GET  /api/v2/reports/rewards/        — hoa hồng theo client+ngày (phân trang)
  GET  /api/reports/rewards/byday/     — hoa hồng tổng hợp theo ngày (không phân trang)

Biến môi trường cần thiết:
  EXNESS_LOGIN      — email đăng nhập Exness Partner Area
  EXNESS_PASSWORD   — mật khẩu
  EXNESS_BASE_URL   — mặc định https://my.exnessaffiliates.com
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.adapters.base import BaseExchangeAdapter, GenericDailyCommission, NormalizedUser
from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.exness_base_url.rstrip("/")
PAGE_SIZE = 500          # max records per request
TOKEN_TTL_SECONDS = 82800  # 23 giờ — làm mới trước khi hết hạn


class ExnessAdapter(BaseExchangeAdapter):
    """
    Adapter sàn Exness — Partnership API v2.

    Flow:
      1. POST /api/v2/auth/ → JWT token (cache 23h)
      2. GET  /api/v2/reports/clients/ → danh sách client (all-time totals)
      3. GET  /api/v2/reports/rewards/ → commission per-client per-day
    """

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._token_fetched_at: Optional[datetime] = None

    @property
    def exchange_id(self) -> str:
        return "exness"

    # ── Authentication ──────────────────────────────────────────────────────────

    async def _get_token(self, client: httpx.AsyncClient, force_refresh: bool = False) -> str:
        """Trả về JWT token hợp lệ, tự động làm mới nếu cần."""
        now = datetime.now(tz=timezone.utc)
        if (
            not force_refresh
            and self._token
            and self._token_fetched_at
            and (now - self._token_fetched_at).total_seconds() < TOKEN_TTL_SECONDS
        ):
            return self._token

        logger.info("[Exness] Đang lấy JWT token...")
        resp = await client.post(
            f"{BASE_URL}/api/v2/auth/",
            json={"login": settings.exness_login, "password": settings.exness_password},
            timeout=15,
        )
        if resp.status_code == 401:
            raise RuntimeError(f"Exness auth thất bại: {resp.text}")
        resp.raise_for_status()

        self._token = resp.json()["token"]
        self._token_fetched_at = now
        logger.info("[Exness] Lấy JWT token thành công")
        return self._token

    def _auth_header(self, token: str) -> Dict[str, str]:
        return {"Authorization": f"JWT {token}"}

    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """GET với auto-retry khi token hết hạn."""
        token = await self._get_token(client)
        for attempt in range(2):
            resp = await client.get(
                f"{BASE_URL}{path}",
                headers=self._auth_header(token),
                params=params or {},
                timeout=30,
            )
            if resp.status_code == 401 and attempt == 0:
                # Token có thể đã hết hạn — lấy lại
                logger.warning("[Exness] Token hết hạn, đang làm mới...")
                token = await self._get_token(client, force_refresh=True)
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("Exness API: không thể xác thực sau 2 lần thử")

    # ── fetch_referrals ─────────────────────────────────────────────────────────

    async def fetch_referrals(self, commission_days: int = 30) -> List[NormalizedUser]:
        """
        Lấy danh sách client từ /api/v2/reports/clients/ (all-time totals).
        commission_days không dùng trực tiếp vì endpoint trả về all-time aggregates,
        nhưng được giữ để tương thích với interface.
        """
        if not settings.exness_login or not settings.exness_password:
            raise RuntimeError(
                "Exness: chưa cấu hình EXNESS_LOGIN và EXNESS_PASSWORD trong .env — không có dữ liệu giả."
            )

        users: List[NormalizedUser] = []
        offset = 0

        try:
            async with httpx.AsyncClient() as client:
                while True:
                    data = await self._get(
                        client,
                        "/api/v2/reports/clients/",
                        params={"limit": PAGE_SIZE, "offset": offset},
                    )
                    rows: List[Dict[str, Any]] = data.get("data", [])
                    if not rows:
                        break

                    for row in rows:
                        users.append(self._normalize_client(row))

                    if len(rows) < PAGE_SIZE:
                        break
                    offset += PAGE_SIZE

        except Exception as exc:
            logger.error("[Exness] fetch_referrals lỗi: %s", exc)
            raise

        logger.info("[Exness] Tải về %d clients", len(users))
        return users

    def _normalize_client(self, row: Dict[str, Any]) -> NormalizedUser:
        reg_str = row.get("reg_date") or row.get("registration_date")
        try:
            registered_at = datetime.fromisoformat(str(reg_str)) if reg_str else datetime.utcnow()
        except ValueError:
            registered_at = datetime.utcnow()

        client_uid = str(row.get("client_uid") or row.get("client_account") or "")
        volume_mln = float(row.get("volume_mln_usd") or 0)
        volume_usd = volume_mln * 1_000_000  # chuyển từ triệu USD → USD

        # deposit_amount là số nguyên (USD)
        deposit = float(row.get("deposit_amount") or 0)
        commission = float(row.get("reward_usd") or 0)
        status_raw = str(row.get("client_status") or "").lower()

        # Exness status: "active", "inactive", "registered" ...
        status = "active" if "active" in status_raw or float(row.get("volume_lots") or 0) > 0 else "inactive"

        return NormalizedUser(
            user_id=client_uid,
            username=client_uid,
            email="",
            registered_at=registered_at,
            total_deposit=deposit,
            total_volume=volume_usd,
            total_commission=commission,
            status=status,
            raw_data=row,
        )

    # ── fetch_daily_commissions_raw ─────────────────────────────────────────────

    async def fetch_daily_commissions_raw(self, days_back: int = 30) -> List[GenericDailyCommission]:
        """
        Lấy hoa hồng per-client per-day từ /api/reports/rewards/ (v1).
        Endpoint v1 không yêu cầu aggregate_by — trả về từng row per client_uid + reward_date.
        Nhóm theo (client_uid, reward_date) vì một client có thể có nhiều account.

        Nếu v1 thất bại, fallback sang /api/reports/rewards/byday/ (tổng hợp theo ngày,
        dùng user_id='all' cho DailyCommission).
        """
        if not settings.exness_login or not settings.exness_password:
            return []

        today = date.today()
        date_from = (today - timedelta(days=days_back)).isoformat()
        date_to = today.isoformat()

        try:
            result = await self._fetch_rewards_v1(date_from, date_to)
            logger.info("[Exness] fetch_daily_commissions_raw: %d records (%s → %s)", len(result), date_from, date_to)
            return result
        except Exception as exc:
            logger.warning("[Exness] v1 rewards thất bại (%s), fallback sang byday...", exc)

        # Fallback: aggregate theo ngày, user_id = "all"
        try:
            return await self._fetch_rewards_byday(date_from, date_to)
        except Exception as exc2:
            logger.error("[Exness] fetch_daily_commissions_raw fallback cũng thất bại: %s", exc2)
            raise

    async def _fetch_rewards_v1(self, date_from: str, date_to: str) -> List[GenericDailyCommission]:
        """
        Dùng /api/reports/rewards/ (v1) — không yêu cầu aggregate_by.
        Mỗi row = 1 client_account × 1 reward_date.
        Gom lại theo (client_uid, reward_date).
        """
        agg: Dict[tuple, Dict[str, float]] = defaultdict(
            lambda: {"trading_volume": 0.0, "commission_volume": 0.0}
        )
        offset = 0
        total_rows = 0

        async with httpx.AsyncClient() as client:
            while True:
                data = await self._get(
                    client,
                    "/api/reports/rewards/",
                    params={
                        "reward_date_from": date_from,
                        "reward_date_to": date_to,
                        "limit": PAGE_SIZE,
                        "offset": offset,
                    },
                )
                rows: List[Dict[str, Any]] = data.get("data", [])
                if not rows:
                    break

                for row in rows:
                    uid = str(row.get("client_uid") or row.get("client_account") or "")
                    reward_date_str = str(row.get("reward_date") or "")
                    if not uid or not reward_date_str:
                        continue
                    try:
                        rd = date.fromisoformat(reward_date_str[:10])
                    except ValueError:
                        continue

                    key = (uid, rd)
                    volume_mln = float(row.get("volume_mln_usd") or 0)
                    agg[key]["trading_volume"] += volume_mln * 1_000_000
                    agg[key]["commission_volume"] += float(row.get("reward_usd") or 0)

                total_rows += len(rows)
                if len(rows) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE

        logger.info("[Exness] v1 rewards: %d rows → %d aggregated records", total_rows, len(agg))
        return [
            GenericDailyCommission(
                uid=uid,
                commission_date=rd,
                trading_volume=vals["trading_volume"],
                commission_volume=vals["commission_volume"],
            )
            for (uid, rd), vals in agg.items()
        ]

    async def _fetch_rewards_byday(self, date_from: str, date_to: str) -> List[GenericDailyCommission]:
        """
        Fallback: /api/reports/rewards/byday/ — tổng hợp toàn bộ theo ngày (không per-client).
        Lưu với user_id='all' để vẫn có time-series.
        """
        async with httpx.AsyncClient() as client:
            data = await self._get(
                client,
                "/api/reports/rewards/byday/",
                params={"reward_date_from": date_from, "reward_date_to": date_to},
            )
        rows: List[Dict[str, Any]] = data.get("data", [])
        result = []
        for row in rows:
            rd_str = str(row.get("reward_date") or "")
            if not rd_str:
                continue
            try:
                rd = date.fromisoformat(rd_str[:10])
            except ValueError:
                continue
            volume_mln = float(row.get("volume_mln_usd") or 0)
            result.append(GenericDailyCommission(
                uid="all",
                commission_date=rd,
                trading_volume=volume_mln * 1_000_000,
                commission_volume=float(row.get("reward_usd") or 0),
            ))
        logger.info("[Exness] byday fallback: %d daily records", len(result))
        return result
