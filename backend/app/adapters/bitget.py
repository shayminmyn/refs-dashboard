import base64
import hashlib
import hmac
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import httpx

from app.adapters.base import BaseExchangeAdapter, NormalizedUser
from app.config import settings

logger = logging.getLogger(__name__)


class BitgetAdapter(BaseExchangeAdapter):
    """
    Adapter sàn Bitget — Broker/Affiliate API.
    Tài liệu: https://www.bitget.com/api-doc/common/intro

    Biến môi trường: BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE, BITGET_BASE_URL
    Nếu chưa cấu hình key, adapter sẽ trả về dữ liệu mock để test.
    """

    @property
    def exchange_id(self) -> str:
        return "bitget"

    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        message = f"{timestamp}{method}{path}{body}"
        mac = hmac.new(
            settings.bitget_api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        )
        return base64.b64encode(mac.digest()).decode()

    async def fetch_referrals(self, commission_days: int = 30) -> List[NormalizedUser]:
        if not settings.bitget_api_key or not settings.bitget_api_secret:
            logger.warning("[Bitget] Chưa cấu hình API key — dùng dữ liệu mock")
            return self._mock_data()

        path = "/api/v2/broker/account/info"
        timestamp = str(int(time.time() * 1000))
        signature = self._sign(timestamp, "GET", path)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{settings.bitget_base_url}{path}",
                    headers={
                        "ACCESS-KEY": settings.bitget_api_key,
                        "ACCESS-SIGN": signature,
                        "ACCESS-TIMESTAMP": timestamp,
                        "ACCESS-PASSPHRASE": settings.bitget_api_passphrase,
                        "Content-Type": "application/json",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                rows: List[Dict[str, Any]] = resp.json().get("data", [])
                return [self._normalize(row) for row in rows]
        except Exception as exc:
            logger.error("[Bitget] fetch_referrals lỗi: %s", exc)
            raise

    def _normalize(self, row: Dict[str, Any]) -> NormalizedUser:
        volume = float(row.get("totalTradeVolume") or 0)
        return NormalizedUser(
            user_id=str(row.get("uid") or row.get("userId") or ""),
            username=str(row.get("nickName") or ""),
            email=str(row.get("email") or ""),
            registered_at=(
                datetime.utcfromtimestamp(int(row["createTime"]) / 1000)
                if row.get("createTime")
                else datetime.utcnow()
            ),
            total_deposit=float(row.get("totalDepositAmount") or 0),
            total_volume=volume,
            total_commission=float(row.get("totalRebateAmount") or 0),
            status="active" if volume > 0 else "inactive",
            raw_data=row,
        )

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
