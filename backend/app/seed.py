"""首次启动时把参考看板的真实数据导入空库，让前端立即可用。

种子文件位于 backend/seed/*.json，来源于历史 yoy-analysis.html。
预算的 year 统一标记为 2026（参考看板口径）。
"""

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Actual, Budget, CompetitorPrice

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
BUDGET_YEAR = 2026


async def seed_if_empty(db: AsyncSession) -> None:
    count = await db.scalar(select(func.count()).select_from(Actual))
    if count and count > 0:
        return

    actuals = json.loads((SEED_DIR / "actuals.json").read_text(encoding="utf-8"))
    # 源数据存在相同维度键的多行（更细分类），按键求和聚合到 (年,月,洲际,二级,三级)
    agg: dict[tuple, list[float]] = {}
    for r in actuals:
        key = (int(r["year"]), int(r["month"]), r["region"], r["l2"], r["l3"])
        acc = agg.setdefault(key, [0.0, 0.0, 0.0])
        acc[0] += float(r.get("revenue") or 0)
        acc[1] += float(r.get("gross") or 0)
        acc[2] += float(r.get("contrib") or 0)
    for (year, month, region, l2, l3), (rev, gross, contrib) in agg.items():
        db.add(
            Actual(
                year=year, month=month, region=region, l2=l2, l3=l3,
                revenue=rev, gross=gross, contrib=contrib,
            )
        )

    sign = json.loads((SEED_DIR / "budget_sign.json").read_text(encoding="utf-8"))
    for r in sign:
        db.add(
            Budget(
                year=BUDGET_YEAR, month=int(r["month"]),
                region=r["region"], l2=r["l2"], caliber="sign",
                revenue=r.get("budget_rev") or 0,
                gross=r.get("budget_gross") or 0,
                contrib=r.get("budget_contrib") or 0,
            )
        )

    op = json.loads((SEED_DIR / "budget_op.json").read_text(encoding="utf-8"))
    for r in op:
        db.add(
            Budget(
                year=BUDGET_YEAR, month=int(r["month"]),
                region=r["region"], l2=r["l2"], caliber="op",
                revenue=r.get("op_rev") or 0,
                gross=r.get("op_gross") or 0,
                contrib=r.get("op_contrib") or 0,
            )
        )

    await db.commit()


async def seed_competitor_if_empty(db: AsyncSession) -> None:
    count = await db.scalar(select(func.count()).select_from(CompetitorPrice))
    if count and count > 0:
        return
    fp = SEED_DIR / "competitor_prices.json"
    if not fp.exists():
        return
    for r in json.loads(fp.read_text(encoding="utf-8")):
        db.add(
            CompetitorPrice(
                vendor=r["vendor"], biz=r.get("biz", ""), country=r["country"],
                service=r["service"], carrier=r.get("carrier", "") or "",
                weight_tier=r.get("weight_tier") or "", size_type=r.get("size_type") or "",
                zone=r.get("zone", "") or "", currency=r.get("currency", "") or "",
                price=r.get("price") or 0, unit=r.get("unit", "") or "",
                note=r.get("note", "") or "",
            )
        )
    await db.commit()
