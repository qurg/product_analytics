"""预算达成 / 同比分析的聚合逻辑。

数据量很小（数百行），直接拉到内存里用 Python 聚合，逻辑清晰、易维护。
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Actual, Budget

# expense(费用)=毛利−贡献利润，派生；其余直接取列
METRICS = ("revenue", "cost", "gross", "expense", "contrib")


def _num(v) -> float:
    return float(v) if v is not None else 0.0


def _metric_value(obj, metric: str) -> float:
    if metric == "expense":
        return _num(obj.gross) - _num(obj.contrib)
    return _num(getattr(obj, metric))


async def build_analysis(
    db: AsyncSession,
    *,
    metric: str = "revenue",
    caliber: str = "sign",
    cur_year: int = 2026,
    prev_year: int = 2025,
    region: str | None = None,
    l2: str | None = None,
    l3: str | None = None,
    month: int | None = None,
) -> dict:
    if metric not in METRICS:
        metric = "revenue"

    # ---- 实际数 ----
    aq = select(Actual)
    if region:
        aq = aq.where(Actual.region == region)
    if l2:
        aq = aq.where(Actual.l2 == l2)
    if l3:
        aq = aq.where(Actual.l3 == l3)
    actuals = (await db.execute(aq)).scalars().all()

    # ---- 预算数（两个口径全取：成本/预算线按需选口径，签约/操作收入两条系列都要用）----
    # 成本=财报成本，统一取操作口径(操作成本=财报成本)，不随所选口径变成目标成本
    budget_caliber = "op" if metric == "cost" else caliber
    bq = select(Budget).where(Budget.year == cur_year)
    if region:
        bq = bq.where(Budget.region == region)
    if l2:
        bq = bq.where(Budget.l2 == l2)
    budgets_all = (await db.execute(bq)).scalars().all()
    budgets = [b for b in budgets_all if b.caliber == budget_caliber]
    # 选了三级产品时预算无法对应到 l3，预算线置空
    budget_disabled = bool(l3)

    def m(obj) -> float:
        return _metric_value(obj, metric)

    # 本年有实际数的月份 = 可比期间（避免拿本年至今 vs 上年全年这种错配）
    cur_months = {a.month for a in actuals if a.year == cur_year}

    # ---- 月度对比（始终覆盖全部 12 个月，不受选中月份影响）----
    months = list(range(1, 13))
    prev_by_m = defaultdict(float)
    cur_by_m = defaultdict(float)
    bud_by_m = defaultdict(float)
    for a in actuals:
        if a.year == prev_year:
            prev_by_m[a.month] += m(a)
        elif a.year == cur_year:
            cur_by_m[a.month] += m(a)
    if not budget_disabled:
        for b in budgets:
            bud_by_m[b.month] += m(b)

    def yoy(cur: float, prev: float):
        if prev == 0:
            return None
        return round((cur - prev) / abs(prev) * 100, 1)

    monthly = [
        {
            "month": mo,
            "prev": round(prev_by_m[mo], 2),
            "cur": round(cur_by_m[mo], 2),
            "budget": None if budget_disabled else round(bud_by_m[mo], 2),
            # 同比只在本年有实际数的月份计算，其余置空（不画到 -100%）
            "yoy": yoy(cur_by_m[mo], prev_by_m[mo]) if mo in cur_months else None,
        }
        for mo in months
    ]

    # ---- 统计口径：选中某月则该月，否则本年可比期间；KPI/拆分/同比都用它 ----
    scope = {month} if month else cur_months

    def in_scope(o) -> bool:
        return o.month in scope

    acts = [a for a in actuals if in_scope(a)]
    buds = [b for b in budgets if in_scope(b)]
    buds_all = [b for b in budgets_all if in_scope(b)]

    # ---- 按维度拆分：本年实际 / 预算 / 签约收入 / 操作收入 ----
    def breakdown(dim: str) -> list[dict]:
        cur_d = defaultdict(float)
        bud_d = defaultdict(float)
        sign_d = defaultdict(float)
        op_d = defaultdict(float)
        for a in acts:
            if a.year == cur_year:
                cur_d[getattr(a, dim)] += m(a)
        has_budget_dim = dim in ("region", "l2")
        if not budget_disabled and has_budget_dim:
            for b in buds:
                bud_d[getattr(b, dim)] += m(b)
            for b in buds_all:  # 签约/操作收入两条系列（始终是收入）
                if b.caliber == "sign":
                    sign_d[getattr(b, dim)] += _num(b.revenue)
                elif b.caliber == "op":
                    op_d[getattr(b, dim)] += _num(b.revenue)
        keys = sorted(set(cur_d) | set(bud_d) | set(sign_d) | set(op_d))
        rows = []
        for k in keys:
            bud = None if (budget_disabled or not has_budget_dim) else round(bud_d[k], 2)
            cur = round(cur_d[k], 2)
            rate = round(cur / bud * 100, 1) if bud not in (None, 0) else None
            rows.append({
                "name": k,
                "cur": cur,
                "budget": bud,
                "rate": rate,
                "sign_rev": round(sign_d[k], 2) if has_budget_dim else None,
                "op_rev": round(op_d[k], 2) if has_budget_dim else None,
            })
        return rows

    by_region = breakdown("region")
    by_l2 = breakdown("l2")
    by_l3 = breakdown("l3")

    # ---- KPI 汇总（选中月份则为该月，否则全年）----
    cur_total = sum(m(a) for a in acts if a.year == cur_year)
    prev_total = sum(m(a) for a in acts if a.year == prev_year)
    bud_total = None if budget_disabled else sum(m(b) for b in buds)
    # 去年累计：上年全年合计（不受可比期间/选中月份影响，作参考）
    prev_full_total = sum(m(a) for a in actuals if a.year == prev_year)
    # 今年全年预算合计（全 12 个月，不受可比期间影响）
    budget_full_total = None if budget_disabled else sum(m(b) for b in budgets)
    kpis = {
        "cur_total": round(cur_total, 2),
        "prev_total": round(prev_total, 2),
        "prev_full_total": round(prev_full_total, 2),
        "budget_full_total": None if budget_full_total is None else round(budget_full_total, 2),
        "budget_total": None if bud_total is None else round(bud_total, 2),
        "yoy": yoy(cur_total, prev_total),
        "achieve_rate": (
            None if not bud_total else round(cur_total / bud_total * 100, 1)
        ),
    }

    return {
        "metric": metric,
        "caliber": caliber,
        "cur_year": cur_year,
        "prev_year": prev_year,
        "month": month,
        "cur_months": sorted(cur_months),
        "budget_disabled": budget_disabled,
        "kpis": kpis,
        "monthly": monthly,
        "by_region": by_region,
        "by_l2": by_l2,
        "by_l3": by_l3,
    }
