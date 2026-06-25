# 产品分析系统 (Product Analytics)

公司级产品分析平台。第一阶段：**预算管理 / 预算达成同比分析**。后续模块：竞对价格对比、非标方案折扣对比。

## 技术栈

- 后端：FastAPI + SQLAlchemy(async) + PostgreSQL
- 前端：Vue3 + Vite + ECharts
- 部署：Docker Compose（自带 PostgreSQL）

## 模块

### 预算分析（已完成）
- 维度：洲际 / 二级产品 / 三级产品；指标：收入 / 毛利 / 贡献利润；口径：签约 / 操作
- 月度对比（上年实际 vs 本年实际 vs 本年预算 + 同比%）、洲际对比、二级产品对比
- KPI：本年累计、同比、预算、达成率、上年累计
- 数据来源：Excel 导入（实际数 + 预算，覆盖式 upsert）
- 首次启动自动用历史看板数据做种子，开箱即用

## 本地开发

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 可改成 sqlite 零配置
uvicorn app.main:app --reload --port 8090

# 前端
cd web
npm install
npm run dev                   # http://localhost:5173 （已代理 /api -> 8090）
```

## Docker 部署

```bash
docker compose up -d --build
# 前端: http://<host>:3010
# 后端: http://<host>:8090/api/health
```

## API

- `GET  /api/budget/dimensions` 维度选项
- `GET  /api/budget/analysis?metric=&caliber=&region=&l2=&l3=` 分析数据
- `POST /api/budget/import/actual` 导入实际数 (multipart: file, default_year?)
- `POST /api/budget/import/budget` 导入预算 (multipart: file, caliber, year)
- `GET  /api/budget/imports` 导入记录
