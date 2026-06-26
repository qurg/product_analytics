"""目标成本（海运先行）：线路主数据 + 时间序列 tracking。

录入以"开一期批量保存"为主力，辅以单条增改与 Excel 导入。
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import CostLane, CostTrack

router = APIRouter(prefix="/api/cost", tags=["cost"])


def lane_dict(l: CostLane) -> dict:
    return {
        "id": l.id, "biz_type": l.biz_type, "lane": l.lane,
        "transport_type": l.transport_type,
        "origin_ports": l.origin_ports, "dest_ports": l.dest_ports,
        "warehouse_code": l.warehouse_code, "warehouse_name": l.warehouse_name,
        "warehouse_type": l.warehouse_type, "country": l.country, "region": l.region,
        "pd": l.pd, "carrier": l.carrier, "container_type": l.container_type,
        "unit": l.unit, "currency": l.currency,
        "extra_fee": float(l.extra_fee) if l.extra_fee is not None else None,
        "extra_fee_name": l.extra_fee_name, "note": l.note,
    }


def _scope(q, biz_type, transport_type):
    q = q.where(CostLane.biz_type == biz_type)
    if transport_type:
        q = q.where(CostLane.transport_type == transport_type)
    return q


@router.get("/lanes")
async def lanes(biz_type: str = "海运", transport_type: str | None = None,
                db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        _scope(select(CostLane), biz_type, transport_type).order_by(CostLane.id)
    )).scalars().all()
    return [lane_dict(l) for l in rows]


class LaneIn(BaseModel):
    biz_type: str = "海运"
    lane: str
    origin_ports: str = ""
    dest_ports: str = ""
    pd: str = ""
    carrier: str = ""
    container_type: str = ""
    unit: str = "FEU"
    currency: str = "USD"
    extra_fee: float | None = None
    extra_fee_name: str = "起运港费用"
    note: str = ""


@router.post("/lanes")
async def create_lane(body: LaneIn, db: AsyncSession = Depends(get_db)):
    obj = CostLane(**body.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return lane_dict(obj)


@router.put("/lanes/{lane_id}")
async def update_lane(lane_id: int, body: LaneIn, db: AsyncSession = Depends(get_db)):
    obj = await db.get(CostLane, lane_id)
    if not obj:
        return {"error": "not found"}
    for k, v in body.model_dump().items():
        setattr(obj, k, v)
    await db.commit()
    return lane_dict(obj)


@router.delete("/lanes/{lane_id}")
async def delete_lane(lane_id: int, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(CostTrack).where(CostTrack.lane_id == lane_id))
    obj = await db.get(CostLane, lane_id)
    if obj:
        await db.delete(obj)
    await db.commit()
    return {"ok": True}


@router.get("/trend")
async def trend(biz_type: str = "海运", transport_type: str | None = None,
                lane: str | None = None, db: AsyncSession = Depends(get_db)):
    """每条线路的目标成本时间序列（喂折线图）。"""
    lq = _scope(select(CostLane), biz_type, transport_type)
    if lane:
        lq = lq.where(CostLane.lane == lane)
    lanes = (await db.execute(lq.order_by(CostLane.id))).scalars().all()
    out = []
    for l in lanes:
        ts = (await db.execute(
            select(CostTrack).where(CostTrack.lane_id == l.id)
            .order_by(CostTrack.effective_date)
        )).scalars().all()
        out.append({
            "lane": l.lane, "transport_type": l.transport_type,
            "country": l.country, "unit": l.unit, "currency": l.currency,
            "points": [{
                "effective_date": t.effective_date.isoformat(),
                "end_date": t.end_date.isoformat() if t.end_date else None,
                "amount": float(t.amount), "id": t.id, "source": t.source,
            } for t in ts],
        })
    return {"biz_type": biz_type, "series": out}


@router.get("/current")
async def current(biz_type: str = "海运", transport_type: str | None = None,
                  as_of: str | None = None, db: AsyncSession = Depends(get_db)):
    """各线路当前生效目标成本 + 环比上一期涨跌（变动预警）。"""
    today = date.fromisoformat(as_of) if as_of else date.today()
    lanes = (await db.execute(
        _scope(select(CostLane), biz_type, transport_type).order_by(CostLane.id)
    )).scalars().all()
    rows = []
    for l in lanes:
        ts = (await db.execute(
            select(CostTrack).where(CostTrack.lane_id == l.id)
            .order_by(CostTrack.effective_date)
        )).scalars().all()
        base = {
            "lane": l.lane, "unit": l.unit, "currency": l.currency,
            "transport_type": l.transport_type, "country": l.country,
            "dest_ports": l.dest_ports, "carrier": l.carrier,
            "extra_fee": float(l.extra_fee) if l.extra_fee is not None else None,
        }
        if not ts:
            # 无历史价（如空运待录入）：仍列出，标"待录入"
            rows.append({**base, "amount": None, "effective_date": None,
                         "end_date": None, "prev_amount": None, "change_pct": None,
                         "pending": True})
            continue
        cur = None
        for t in ts:
            if t.effective_date <= today and (t.end_date is None or t.end_date >= today):
                cur = t
        if cur is None:
            cur = ts[-1]  # 兜底取最新一期
        idx = ts.index(cur)
        prev = ts[idx - 1] if idx > 0 else None
        chg = None
        if prev and float(prev.amount):
            chg = round((float(cur.amount) - float(prev.amount)) / float(prev.amount) * 100, 1)
        rows.append({
            **base,
            "amount": float(cur.amount),
            "effective_date": cur.effective_date.isoformat(),
            "end_date": cur.end_date.isoformat() if cur.end_date else None,
            "prev_amount": float(prev.amount) if prev else None,
            "change_pct": chg, "pending": False,
        })
    return {"biz_type": biz_type, "as_of": today.isoformat(), "rows": rows}


@router.get("/last_period")
async def last_period(biz_type: str = "海运", transport_type: str | None = None,
                      db: AsyncSession = Depends(get_db)):
    """开新一期时预填：各线路最新一期的价格 + 建议的新生效日期。"""
    lanes = (await db.execute(
        _scope(select(CostLane), biz_type, transport_type).order_by(CostLane.id)
    )).scalars().all()
    rows = []
    latest_end = None
    for l in lanes:
        t = (await db.execute(
            select(CostTrack).where(CostTrack.lane_id == l.id)
            .order_by(CostTrack.effective_date.desc()).limit(1)
        )).scalars().first()
        rows.append({
            "lane_id": l.id, "lane": l.lane, "unit": l.unit, "currency": l.currency,
            "transport_type": l.transport_type, "country": l.country,
            "last_amount": float(t.amount) if t else None,
            "last_end": t.end_date.isoformat() if t and t.end_date else None,
        })
        if t and t.end_date and (latest_end is None or t.end_date > latest_end):
            latest_end = t.end_date
    suggest_eff = (latest_end + timedelta(days=1)).isoformat() if latest_end else None
    return {"biz_type": biz_type, "rows": rows, "suggest_effective": suggest_eff}


class TrackItem(BaseModel):
    lane_id: int
    amount: float | None = None


class BatchIn(BaseModel):
    biz_type: str = "海运"
    effective_date: str
    end_date: str | None = None
    items: list[TrackItem]


@router.post("/track/batch")
async def save_batch(body: BatchIn, db: AsyncSession = Depends(get_db)):
    """开一期批量保存：跳过空值，按 (线路,生效日期) 覆盖。"""
    eff = date.fromisoformat(body.effective_date)
    end = date.fromisoformat(body.end_date) if body.end_date else None
    n = 0
    for it in body.items:
        if it.amount is None:
            continue
        # 同线路同生效日期 → 覆盖
        existing = (await db.execute(
            select(CostTrack).where(
                CostTrack.lane_id == it.lane_id, CostTrack.effective_date == eff
            )
        )).scalars().first()
        if existing:
            existing.amount = it.amount
            existing.end_date = end
            existing.source = "手工"
        else:
            db.add(CostTrack(lane_id=it.lane_id, effective_date=eff, end_date=end,
                             amount=it.amount, source="手工"))
        n += 1
    await db.commit()
    return {"saved": n}


class TrackIn(BaseModel):
    lane_id: int
    effective_date: str
    end_date: str | None = None
    amount: float


@router.put("/track/{tid}")
async def update_track(tid: int, body: TrackIn, db: AsyncSession = Depends(get_db)):
    obj = await db.get(CostTrack, tid)
    if not obj:
        return {"error": "not found"}
    obj.lane_id = body.lane_id
    obj.effective_date = date.fromisoformat(body.effective_date)
    obj.end_date = date.fromisoformat(body.end_date) if body.end_date else None
    obj.amount = body.amount
    obj.source = "手工"
    await db.commit()
    return {"ok": True}


@router.delete("/track/{tid}")
async def delete_track(tid: int, db: AsyncSession = Depends(get_db)):
    obj = await db.get(CostTrack, tid)
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}
