from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, func
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


class CostLane(Base):
    """目标成本-线路主数据（固定属性，建一次少动）。海运先行，结构兼容跨境/小包。"""

    __tablename__ = "cost_lanes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    biz_type: Mapped[str] = mapped_column(String(16), index=True)  # 海运/跨境到仓/小包
    lane: Mapped[str] = mapped_column(String(64), index=True)      # 线路名/目的仓名
    transport_type: Mapped[str] = mapped_column(String(8), default="")  # 空运/海运(跨境用)
    origin_ports: Mapped[str] = mapped_column(String(255), default="")  # 起运港
    dest_ports: Mapped[str] = mapped_column(String(255), default="")    # 目的港
    warehouse_code: Mapped[str] = mapped_column(String(64), default="")
    warehouse_name: Mapped[str] = mapped_column(String(64), default="")
    warehouse_type: Mapped[str] = mapped_column(String(16), default="")
    country: Mapped[str] = mapped_column(String(16), default="")
    region: Mapped[str] = mapped_column(String(16), default="")  # 海运区域(目的港归属)
    pd: Mapped[str] = mapped_column(String(64), default="")
    carrier: Mapped[str] = mapped_column(String(64), default="")        # 船东
    container_type: Mapped[str] = mapped_column(String(16), default="") # 柜型
    unit: Mapped[str] = mapped_column(String(16), default="")           # 计费单位 FEU
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    extra_fee: Mapped[float] = mapped_column(Numeric(18, 2), nullable=True)  # 起运港费
    extra_fee_name: Mapped[str] = mapped_column(String(32), default="")
    note: Mapped[str] = mapped_column(String(255), default="")


class CostTrack(Base):
    """目标成本-时间序列（每期变动的就这条）。"""

    __tablename__ = "cost_track"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lane_id: Mapped[int] = mapped_column(Integer, index=True)
    effective_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2))
    source: Mapped[str] = mapped_column(String(16), default="手工")  # 导入/手工
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
