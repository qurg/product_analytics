from pydantic import BaseModel


class Dimensions(BaseModel):
    years: list[int]
    regions: list[str]
    l2s: list[str]
    # 三级产品 -> 所属二级产品 的映射，前端做联动下拉
    l3_to_l2: dict[str, str]


class ImportResult(BaseModel):
    kind: str
    filename: str
    rows: int
    note: str = ""


class ImportLogOut(BaseModel):
    id: int
    kind: str
    filename: str
    rows: int
    note: str
    created_at: str
