from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import Actual, ImportLog
from ..schemas import Dimensions, ImportResult
from ..services.analysis import build_analysis
from ..services.excel_import import (
    import_actuals,
    import_budgets,
    import_workbook,
)

router = APIRouter(prefix="/api/budget", tags=["budget"])


@router.get("/dimensions", response_model=Dimensions)
async def dimensions(db: AsyncSession = Depends(get_db)):
    years = sorted((await db.execute(select(distinct(Actual.year)))).scalars().all())
    regions = sorted(
        (await db.execute(select(distinct(Actual.region)))).scalars().all()
    )
    l2s = sorted((await db.execute(select(distinct(Actual.l2)))).scalars().all())
    pairs = (await db.execute(select(Actual.l3, Actual.l2).distinct())).all()
    l3_to_l2 = {l3: l2 for l3, l2 in pairs}
    return Dimensions(years=years, regions=regions, l2s=l2s, l3_to_l2=l3_to_l2)


@router.get("/analysis")
async def analysis(
    metric: str = "revenue",
    caliber: str = "sign",
    cur_year: int = 2026,
    prev_year: int = 2025,
    region: str | None = None,
    l2: str | None = None,
    l3: str | None = None,
    month: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await build_analysis(
        db,
        metric=metric,
        caliber=caliber,
        cur_year=cur_year,
        prev_year=prev_year,
        region=region or None,
        l2=l2 or None,
        l3=l3 or None,
        month=month or None,
    )


@router.post("/import/actual", response_model=ImportResult)
async def import_actual_file(
    file: UploadFile = File(...),
    default_year: int | None = Form(None),
    replace: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    n = await import_actuals(
        db, content, file.filename or "actual.xlsx", default_year, replace
    )
    return ImportResult(kind="actual", filename=file.filename or "", rows=n)


@router.post("/import/budget", response_model=ImportResult)
async def import_budget_file(
    file: UploadFile = File(...),
    caliber: str = Form("sign"),
    year: int = Form(2026),
    replace: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    n = await import_budgets(
        db, content, file.filename or "budget.xlsx", caliber, year, replace
    )
    return ImportResult(
        kind=f"budget-{caliber}", filename=file.filename or "", rows=n
    )


@router.post("/import/workbook")
async def import_workbook_file(
    file: UploadFile = File(...),
    replace: bool = Form(True),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    results = await import_workbook(
        db, content, file.filename or "workbook.xlsx", replace
    )
    return {"filename": file.filename, "replace": replace, "sheets": results}


@router.get("/imports")
async def imports(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(ImportLog).order_by(ImportLog.created_at.desc()))
    ).scalars().all()
    return [
        {
            "id": r.id,
            "kind": r.kind,
            "filename": r.filename,
            "rows": r.rows,
            "note": r.note,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
