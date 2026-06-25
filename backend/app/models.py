from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# 指标统一用 Numeric(18,2) 存储金额，避免浮点误差。
# 维度（洲际 region / 二级产品 l2 / 三级产品 l3）按源数据反规范化为字符串列，
# 下拉选项通过 DISTINCT 查询动态得到，Excel 导入无需解析外键。


class Actual(Base):
    """实际经营数（来自 Excel 导入）：月 × 洲际 × 二级 × 三级 粒度。"""

    __tablename__ = "actuals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer, index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    l2: Mapped[str] = mapped_column(String(128), index=True)
    l3: Mapped[str] = mapped_column(String(128), index=True)
    revenue: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)  # 财报成本
    gross: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    contrib: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    __table_args__ = (
        Index("ix_actual_dims", "year", "month", "region", "l2", "l3", unique=True),
    )


class Budget(Base):
    """预算数（来自 Excel 导入）：月 × 洲际 × 二级 粒度，分签约/操作两套口径。"""

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[int] = mapped_column(Integer, index=True)
    region: Mapped[str] = mapped_column(String(64), index=True)
    l2: Mapped[str] = mapped_column(String(128), index=True)
    # 口径: sign=签约, op=操作
    caliber: Mapped[str] = mapped_column(String(8), index=True)
    revenue: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    # 成本：签约口径=目标成本(转移定价)，操作口径=操作成本
    cost: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    gross: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    contrib: Mapped[float] = mapped_column(Numeric(18, 2), default=0)

    __table_args__ = (
        Index(
            "ix_budget_dims",
            "year",
            "month",
            "region",
            "l2",
            "caliber",
            unique=True,
        ),
    )


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


class ImportLog(Base):
    """导入记录，便于追溯每次 Excel 上传。"""

    __tablename__ = "import_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # actual / budget
    filename: Mapped[str] = mapped_column(String(255))
    rows: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
