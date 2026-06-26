"""首次启动时把竞对价卡种子导入空库，让前端立即可用。

种子文件位于 backend/seed/competitor_prices.json。
"""

import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CompetitorPrice

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


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
