from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional


@dataclass
class GenericDailyCommission:
    """
    Cấu trúc hoa hồng ngày chung — dùng cho các adapter không có breakdown.
    uid: ID người dùng trên sàn (string).
    """
    uid: str
    commission_date: date
    trading_volume: float        # tổng volume (USD)
    commission_volume: float     # tổng hoa hồng (USD)
    spot_volume: float = 0.0
    spot_commission: float = 0.0
    swap_volume: float = 0.0
    swap_commission: float = 0.0
    std_volume: float = 0.0
    std_commission: float = 0.0
    copy_volume: float = 0.0
    copy_commission: float = 0.0


@dataclass
class NormalizedUser:
    user_id: str
    username: str
    registered_at: datetime
    total_deposit: float
    total_volume: float
    total_commission: float
    status: Literal["active", "inactive"]
    email: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)


class BaseExchangeAdapter(ABC):
    """
    Lớp cơ sở cho tất cả adapter sàn giao dịch.
    Để thêm sàn mới, kế thừa lớp này và implement fetch_referrals().
    fetch_daily_commissions_raw() là tùy chọn — ghi đè nếu sàn hỗ trợ.
    """

    @property
    @abstractmethod
    def exchange_id(self) -> str:
        """ID định danh của sàn, ví dụ: 'bingx', 'exness'."""
        ...

    @abstractmethod
    async def fetch_referrals(self, commission_days: int = 30) -> List[NormalizedUser]:
        """
        Lấy danh sách người dùng giới thiệu từ API của sàn.
        commission_days: cửa sở API cho các bước gộp tạm (BingX/Bitget).
        Sau sync, snapshot total_volume / total_commission thường được **rollup**
        từ toàn bộ DailyCommission trong Mongo — xem snapshot_totals_from_daily_rollup().
        Tự xử lý phân trang nội bộ và trả về toàn bộ danh sách.
        """
        ...

    async def fetch_daily_commissions_raw(self, days_back: int = 30) -> List[Any]:
        """
        Tùy chọn: Lấy dữ liệu hoa hồng hàng ngày thô để lưu vào DailyCommission.
        Các adapter không hỗ trợ endpoint này sẽ trả về danh sách rỗng.
        """
        return []

    def snapshot_totals_from_daily_rollup(self) -> bool:
        """
        Sau khi sync DailyCommission, có ghi đè total_volume / total_commission trên
        ReferredUser bằng SUM toàn bộ bản ghi daily trong Mongo hay không.

        True (mặc định): BingX/Bitget — fetch_referrals chỉ gộp theo commission_days;
        rollup phản ánh **toàn bộ lịch sử đã lưu** trong DB.

        False: Exness — API clients đã là all-time; rollup có thể làm nhỏ số nếu DC chỉ có vài ngày.
        """
        return True
