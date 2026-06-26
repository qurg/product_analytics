"""首次启动时把竞对价卡种子导入空库，让前端立即可用。

种子文件位于 backend/seed/competitor_prices.json。
"""

import json
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CompetitorPrice, CostLane, CostTrack

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def _d(s):
    return date.fromisoformat(s) if s else None


async def seed_cost_if_empty(db: AsyncSession) -> None:
    """目标成本：线路主数据 + 历史时间序列（海运）。"""
    count = await db.scalar(select(func.count()).select_from(CostLane))
    if count and count > 0:
        return
    lanes_fp = SEED_DIR / "cost_lanes.json"
    track_fp = SEED_DIR / "cost_track.json"
    if not lanes_fp.exists():
        return
    lane_id = {}
    for r in json.loads(lanes_fp.read_text(encoding="utf-8")):
        obj = CostLane(
            biz_type=r["biz_type"], lane=r["lane"],
            origin_ports=r.get("origin_ports", ""), dest_ports=r.get("dest_ports", ""),
            pd=r.get("pd", ""), carrier=r.get("carrier", ""),
            container_type=r.get("container_type", ""), unit=r.get("unit", ""),
            currency=r.get("currency", "USD"), extra_fee=r.get("extra_fee"),
            extra_fee_name=r.get("extra_fee_name", ""),
        )
        db.add(obj)
        await db.flush()
        lane_id[(r["biz_type"], r["lane"])] = obj.id
    if track_fp.exists():
        for t in json.loads(track_fp.read_text(encoding="utf-8")):
            lid = lane_id.get(("海运", t["lane"]))
            if not lid:
                continue
            db.add(CostTrack(
                lane_id=lid, effective_date=_d(t["effective_date"]),
                end_date=_d(t.get("end_date")), amount=t["amount"],
                source=t.get("source", "导入"),
            ))

    # 跨境到仓（海运+空运），按 目的仓|运输类型 路由
    cb_lanes_fp = SEED_DIR / "cost_lanes_cb.json"
    cb_track_fp = SEED_DIR / "cost_track_cb.json"
    if cb_lanes_fp.exists():
        key_id = {}
        for r in json.loads(cb_lanes_fp.read_text(encoding="utf-8")):
            obj = CostLane(
                biz_type=r["biz_type"], lane=r["lane"],
                transport_type=r.get("transport_type", ""),
                origin_ports=r.get("origin_ports", ""), dest_ports=r.get("dest_ports", ""),
                warehouse_code=r.get("warehouse_code", ""),
                warehouse_name=r.get("warehouse_name", ""),
                warehouse_type=r.get("warehouse_type", ""),
                country=r.get("country", ""), pd=r.get("pd", ""),
                unit=r.get("unit", ""), currency=r.get("currency", "USD"),
            )
            db.add(obj)
            await db.flush()
            key_id[r["_key"]] = obj.id
        if cb_track_fp.exists():
            for t in json.loads(cb_track_fp.read_text(encoding="utf-8")):
                lid = key_id.get(t["key"])
                if not lid:
                    continue
                db.add(CostTrack(
                    lane_id=lid, effective_date=_d(t["effective_date"]),
                    end_date=_d(t.get("end_date")), amount=t["amount"],
                    source=t.get("source", "导入"),
                ))
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
