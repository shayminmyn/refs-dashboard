"""
Registry các adapter sàn giao dịch.

Để thêm sàn mới:
1. Tạo file adapter mới kế thừa BaseExchangeAdapter
2. Import và thêm instance vào danh sách _adapters bên dưới
Không cần thay đổi bất kỳ file nào khác.
"""

from typing import Dict, List, Optional

from app.adapters.base import BaseExchangeAdapter
from app.adapters.bingx import BingXAdapter
from app.adapters.exness import ExnessAdapter

_adapters: List[BaseExchangeAdapter] = [
    BingXAdapter(),
    ExnessAdapter(),
    # BitgetAdapter — tạm gỡ khỏi registry (file adapters/bitget.py vẫn giữ để bật lại sau)
]

_registry: Dict[str, BaseExchangeAdapter] = {a.exchange_id: a for a in _adapters}


def get_adapter(exchange_id: str) -> Optional[BaseExchangeAdapter]:
    return _registry.get(exchange_id)


def get_all_adapters() -> List[BaseExchangeAdapter]:
    return _adapters
