from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import CompetitorPrice

router = APIRouter(prefix="/api/competitor", tags=["competitor"])

OUR = "京东"  # 我司

# 汇率: 1 单位该币种 = 多少 USD (内置近似值, 2026Q2; 可按需调整)。
# 跨币种对比时统一折算后再比, 基准币种取"京东在该国的报价币种"。
FX_USD = {
    "USD": 1.0, "CNY": 0.14, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0064,
    "KRW": 0.00073, "CAD": 0.73, "AUD": 0.66, "PLN": 0.25, "MXN": 0.059,
    "VND": 0.000039, "THB": 0.028, "SGD": 0.74, "HKD": 0.128, "MYR": 0.21,
    "AED": 0.272, "SAR": 0.267, "CZK": 0.043, "SEK": 0.094,
}


def to_ccy(price, frm, base):
    """把 price 从 frm 币种折算到 base 币种; 无汇率则返回 None。"""
    if price is None or not frm or not base:
        return None
    if frm == base:
        return price
    if frm not in FX_USD or base not in FX_USD:
        return None
    return price * FX_USD[frm] / FX_USD[base]


@router.get("/dimensions")
async def dimensions(db: AsyncSession = Depends(get_db)):
    async def uniq(col):
        rows = (await db.execute(select(distinct(col)).where(col != ""))).scalars().all()
        return sorted([x for x in rows if x])

    return {
        "vendors": await uniq(CompetitorPrice.vendor),
        "countries": await uniq(CompetitorPrice.country),
        "services": await uniq(CompetitorPrice.service),
    }


@router.get("/carriers")
async def carriers(country: str, service: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(distinct(CompetitorPrice.carrier)).where(
            CompetitorPrice.country == country,
            CompetitorPrice.service == service,
            CompetitorPrice.carrier != "",
        )
    )).scalars().all()
    return sorted([c for c in rows if c])


@router.get("/zones")
async def zones(country: str, service: str, carrier: str, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(distinct(CompetitorPrice.zone)).where(
            CompetitorPrice.country == country,
            CompetitorPrice.service == service,
            CompetitorPrice.carrier == carrier,
            CompetitorPrice.zone != "",
        )
    )).scalars().all()
    zs = [z for z in rows if z]

    def zkey(z):
        import re
        m = re.findall(r"\d+", z)
        return (0 if z == "统一" else 1, z[0] if z and not z[0].isdigit() else "", int(m[0]) if m else 0)

    return sorted(zs, key=zkey)


@router.get("/compare")
async def compare(
    country: str,
    service: str,
    carrier: str | None = None,
    zone: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """返回该 国家×服务 下，按 档位(重量档/货型) × 厂商 的单价透视，
    并标注最低价厂商、我司(京东)对比最低价的价差%。"""
    q = select(CompetitorPrice).where(
        CompetitorPrice.country == country, CompetitorPrice.service == service
    )
    if carrier:
        q = q.where(CompetitorPrice.carrier == carrier)
    if zone:
        q = q.where(CompetitorPrice.zone == zone)
    rows = (await db.execute(q)).scalars().all()
    if not rows:
        return {"country": country, "service": service, "vendors": [], "rows": []}

    currency = rows[0].currency
    unit = rows[0].unit
    # 基准币种 = 京东在该国的报价币种(我司口径); 无京东数据则取最常见币种
    jd_curs = [r.currency for r in rows if r.vendor == OUR and r.currency]
    if jd_curs:
        base_ccy = Counter(jd_curs).most_common(1)[0][0]
    else:
        all_curs = [r.currency for r in rows if r.currency]
        base_ccy = Counter(all_curs).most_common(1)[0][0] if all_curs else ""
    # 固定四家列（我司京东在前），无数据显示 —，便于看清覆盖缺口
    CANON = [OUR, "4px", "WINIT", "谷仓"]
    present = {r.vendor for r in rows}
    vendors = CANON + sorted(present - set(CANON))
    # 档位键：存储用 size_type，其余用 weight_tier
    use_size = service == "存储"

    def tier_key(r):
        return r.size_type if use_size else r.weight_tier

    # 档位排序
    WEIGHT_ORDER = ["0-0.5", "0.5-1", "1-3", "3-5", "5-8", "5-10", "8-10",
                    "10-15", "10-20", "15-20", "15-22.5", "20-30", "22.5-30",
                    "30-40", "40-50", "50-60", "60-70"]
    SIZE_ORDER = ["T25 轻小","T50 小","T120 中","T240 大","TM 超大","T25","T50","T120","T240","TM","XS/S","M/L/XL","小件","中件","大件","超大件"]
    order = SIZE_ORDER if use_size else WEIGHT_ORDER

    import re

    # 分组键 = (分区, 档位)。未筛选 zone 时一页展示所有分区
    grouped = defaultdict(dict)
    cur_of = defaultdict(dict)
    notes = defaultdict(str)
    zones_set = set()
    for r in rows:
        t = tier_key(r)
        if not t:
            continue
        z = r.zone or "统一"
        zones_set.add(z)
        k = (z, t)
        grouped[k][r.vendor] = float(r.price)
        cur_of[k][r.vendor] = r.currency
        if r.note:
            notes[k] = r.note

    # 档位填充: 计费规则为"重量落入哪档按该档上限收费"。某承运商缺某重量档时,
    # 用其"覆盖该重量的最小档"(即 ≥该重量 的最近档)填充, 便于逐档横比。
    #   单档承运商(如京东 0-20 一口价) -> 各档同价, 标"平价"
    #   多档承运商(阶梯价) -> 取上一档, 标"↑档"
    fill_cells = {}  # (zone,tier,vendor) -> "平价"|"↑档"
    if service == "尾程派送":  # 仅尾程做阶梯/平价填充; 仓内各家计费档差异大, 只显示真实档
        def kgnum(t):
            ts = str(t)
            if "续重" in ts or "oz" in ts or "lb" in ts:
                return None
            m = re.findall(r"[\d.]+", ts)
            return float(m[-1]) if m else None
        for z in zones_set:
            rowtiers = sorted(
                {t for (zz, t) in grouped if zz == z and kgnum(t) is not None},
                key=kgnum)
            vend = defaultdict(list)  # vendor -> [(upper, tier)]
            for t in rowtiers:
                for v in grouped[(z, t)]:
                    vend[v].append((kgnum(t), t))
            for v, lst in vend.items():
                single = len({u for u, _ in lst}) == 1
                for t in rowtiers:
                    if v in grouped[(z, t)]:
                        continue
                    W = kgnum(t)
                    cand = [(u, tt) for u, tt in lst if u >= W]  # 覆盖W的档
                    if not cand:
                        continue  # W 超过该承运商最大档 -> 留空
                    _, src = min(cand)
                    grouped[(z, t)][v] = grouped[(z, src)][v]
                    cur_of[(z, t)][v] = cur_of[(z, src)].get(v)
                    fill_cells[(z, t, v)] = "平价" if single else "↑档"

    multi_zone = len(zones_set) > 1 or (zones_set and "统一" not in zones_set)

    def zsort(z):
        m = re.findall(r"\d+", z)
        return (0 if z == "统一" else 1, z[0] if z and not z[0].isdigit() else "",
                int(m[0]) if m else 0)

    def tsort(t):
        if use_size:
            return (order.index(t) if t in order else 999, 0.0, 0.0)
        ts = str(t)
        if "续重" in ts:                       # 续重/kg 永远排最后
            return (9, 9e9, 0.0)
        nums = re.findall(r"[\d.]+", ts)
        n = float(nums[0]) if nums else 9e9
        if "oz" in ts:                          # oz < lb < kg区间
            return (1, n, 0.0)
        if "lb" in ts:
            return (2, n, 0.0)
        lo = float(nums[0]) if nums else 9e9
        hi = float(nums[1]) if len(nums) > 1 else lo
        return (0, lo, hi)

    out_rows = []
    for k in sorted(grouped, key=lambda x: (zsort(x[0]), tsort(x[1]))):
        z, t = k
        prices = grouped[k]
        valid = {v: p for v, p in prices.items() if p > 0}
        # 折算到基准币种(京东币种)后比较
        conv = {v: to_ccy(p, cur_of[k].get(v), base_ccy) for v, p in valid.items()}
        comparable = {v: cv for v, cv in conv.items() if cv is not None}
        currs = {cur_of[k][v] for v in valid}
        mixed = len(currs) > 1  # 是否发生了跨币种(前端提示用)
        cheapest = min(comparable, key=comparable.get) if comparable else None
        our_c = comparable.get(OUR)
        others_c = {v: cv for v, cv in comparable.items() if v != OUR}
        diff = None
        if our_c is not None and others_c:
            best = min(others_c.values())
            if best:
                diff = round((our_c - best) / best * 100, 1)
        out_rows.append({
            "zone": z,
            "tier": t,
            "prices": {v: prices.get(v) for v in vendors},
            "currencies": {v: cur_of[k].get(v) for v in vendors},
            "conv": {v: (round(conv[v], 4) if conv.get(v) is not None and cur_of[k].get(v) != base_ccy else None) for v in vendors},
            "fill": {v: fill_cells.get((z, t, v), "") for v in vendors},
            "cheapest": cheapest,
            "our_vs_best": diff,
            "mixed_currency": mixed,
            "note": notes.get(k, ""),
        })
    return {
        "country": country,
        "service": service,
        "currency": currency,
        "base_currency": base_ccy,
        "unit": unit,
        "vendors": vendors,
        "our": OUR,
        "multi_zone": multi_zone,
        "rows": out_rows,
    }
