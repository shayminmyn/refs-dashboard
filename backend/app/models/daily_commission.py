from datetime import date, datetime
from typing import Optional
from beanie import Document
from pydantic import Field
from pymongo import IndexModel, ASCENDING, DESCENDING


class DailyCommission(Document):
    """
    Lưu trữ hoa hồng hàng ngày từ API sàn giao dịch.
    Mỗi bản ghi = 1 user × 1 ngày × 1 sàn.
    Dùng để vẽ biểu đồ time-series chi tiết.
    """
    exchange_id: str
    user_id: str                        # UID người dùng trên sàn
    commission_date: date               # Ngày (YYYY-MM-DD)
    trading_volume: float = 0.0         # Tổng volume giao dịch trong ngày (USDT)
    commission_volume: float = 0.0      # Tổng hoa hồng trong ngày (USDT)

    # Breakdown theo loại sản phẩm (BingX)
    spot_volume: float = 0.0
    spot_commission: float = 0.0
    swap_volume: float = 0.0            # Perp futures
    swap_commission: float = 0.0
    std_volume: float = 0.0             # Standard futures
    std_commission: float = 0.0
    copy_volume: float = 0.0            # Copy trade
    copy_commission: float = 0.0

    synced_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "daily_commissions"
        indexes = [
            IndexModel(
                [("exchange_id", ASCENDING), ("user_id", ASCENDING), ("commission_date", ASCENDING)],
                unique=True,
            ),
            IndexModel([("exchange_id", ASCENDING), ("commission_date", DESCENDING)]),
            IndexModel([("commission_date", DESCENDING)]),
        ]
