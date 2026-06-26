from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class CompetitorPrice(Base):
    """竞对价卡（仓内/尾程）。灵活宽表，按需用 weight_tier 或 size_type。"""

    __tablename__ = "competitor_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vendor: Mapped[str] = mapped_column(String(32), index=True)   # 京东/4px/WINIT/谷仓
    biz: Mapped[str] = mapped_column(String(16), index=True)      # 仓内/尾程
    country: Mapped[str] = mapped_column(String(48), index=True)
    service: Mapped[str] = mapped_column(String(48), index=True)  # 入库上架/B2C出库/存储/尾程派送
    carrier: Mapped[str] = mapped_column(String(64), default="")  # 尾程承运商
    weight_tier: Mapped[str] = mapped_column(String(32), default="")
    size_type: Mapped[str] = mapped_column(String(32), default="")
    zone: Mapped[str] = mapped_column(String(32), default="")
    currency: Mapped[str] = mapped_column(String(8), default="")
    price: Mapped[float] = mapped_column(Numeric(18, 4), default=0)
    unit: Mapped[str] = mapped_column(String(32), default="")
    note: Mapped[str] = mapped_column(String(255), default="")
