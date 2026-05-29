# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

flight-scan 是一个个人机票监控工具，通过 Playwright 爬取携程机票数据，进行价格分析和报告生成。React 前端访问 `http://127.0.0.1:5173`，FastAPI 后端通过 Vite 代理 (`/api → localhost:8000`) 提供 JSON API。不再提供服务端渲染页面。

## 启动和常用命令

```bash
# 后端
python run.py                              # 启动 API (http://127.0.0.1:8000)

# 前端
cd frontend && npm run dev                 # 启动开发服务器 (http://127.0.0.1:5173)
cd frontend && npm run build              # 生产构建 (tsc + vite build)
cd frontend && npm run preview              # 预览生产构建

# 测试
python -m pytest tests/                    # 运行所有测试
python -m pytest tests/test_ctrip_parser.py -v  # 运行单个测试文件

# 安装
pip install -r requirements.txt
playwright install chromium
cd frontend && npm install
```

## 技术栈

- **后端**: Python 3.11+, FastAPI, SQLAlchemy 2.0 (同步模式), SQLite, APScheduler, Playwright (同步 API)
- **前端**: React 18, Vite 6, TypeScript, Tailwind CSS, Radix UI primitives, React Router 6, TanStack Query, react-hook-form + zod, Recharts (图表), date-fns (日期处理)
- **LLM**: OpenAI 兼容接口 (通过环境变量 `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` 配置)，用于旅行报告智能分析和购票建议生成。支持 `OPENAI_COMPATIBLE_*` 环境变量别名

## 架构和数据流

### 核心流程

```
FlightMonitor (路线配置 + 日期)
  → FlightScan (一次扫描)
    → FlightQueryBatch / FlightQueryTask (具体查询任务)
      → Playwright 爬虫 → screenshots/HTML/text 存储
      → Parser → FlightPriceRaw (原始价格数据)
      → 往返程展开 → FlightRoundTripOutbound → FlightRoundTripReturn → FlightRoundTripPlan
      → 分析 → FlightPlanResult + FlightBestDaily
      → FlightReport (可选 LLM 增强)
      → 通知 (PushPlus / 企业微信 Webhook)
```

### 后端结构

- `app/main.py` — 应用工厂，CORS 配置，启动时创建表并启动调度器
- `app/db.py` — SQLAlchemy 引擎/session/Base，**无 Alembic**，通过 `ensure_runtime_schema()` 做 ALTER TABLE ADD COLUMN 式迁移
- `app/models.py` — 所有 ORM 模型，使用 SQLAlchemy 2.0 Mapped 风格
- `app/routers/api.py` — **所有 API 端点集中在一个文件中**（monitors, dates, scans, tasks, prices, plans, roundtrips, best, reports, settings, city-codes）
- `app/crawler/ctrip.py` — Playwright 同步爬虫，操作携程航班搜索页面，支持人工接管（登录/验证码）
- `app/parsers/ctrip_parser.py` — 基于 HTMLParser 的可见文本提取和正则匹配解析
- `app/parsers/base.py` — `FlightPriceItem` dataclass
- `app/services/scan_runner.py` — 扫描流水线 (`ScanPipeline`)，编排 6 个步骤：生成任务 → 浏览器搜索 → 保存快照 → 解析价格 → 分析结果 → 生成报告
- `app/services/scan_service.py` — 创建和更新扫描记录
- `app/services/scheduler_service.py` — APScheduler 后台调度器，支持每个 Monitor 独立的 cron 表达式
- `app/services/plan_service.py` — 从价格数据生成候选出行方案
- `app/services/roundtrip_service.py` — 往返程展开策略（NONE / LOWEST_TOP_N / SPECIFIC_RANKS / ALL）
- `app/services/analyze_service.py` — 日度最佳方案分析 (`FlightBestDaily`)
- `app/services/price_parse_service.py` / `task_service.py` / `date_service.py` / `monitor_service.py` / `positioning_service.py` / `transfer_service.py` / `city_code_service.py` / `notify_service.py` / `report_service.py` / `settings_service.py`
- `app/llm.py` — OpenAI 兼容 LLM 调用（用于报告摘要生成）
- `app/constants.py` — 所有字符串常量（状态、平台、查询类型、价格类型等）

### 前端结构

- `src/lib/api.ts` — `apiGet`/`apiPost`/`apiPut`/`apiDelete` 封装，自动识别 Vite 代理 vs 独立部署（通过 `VITE_API_BASE_URL` 环境变量）
- `src/routes.tsx` — 集中式路由定义，所有页面挂在 `<AppLayout>` 下
- `src/api/*.ts` — 每个领域一个 API 模块 (monitorApi, scanApi, taskApi, priceApi, planApi, roundtripApi, bestApi, reportApi, batchApi, overviewApi, settingsApi)
- `src/pages/OverviewPage.tsx` — 仪表盘首页（不分子目录）
- `src/pages/*/` — 页面组件按功能分类 (monitors, scans, batches, tasks, prices, plans, roundtrips, best, reports, settings)
- `src/components/ui/` — shadcn/ui 风格的 Radix 组件封装
- `src/components/common/` — 跨页面共享组件 (StatusBadge, PriceText, RouteCell, StrategyTags, RiskBadge, CalendarGrid, SnapshotLinks 等)
- `src/types/` — TypeScript 类型定义

### 数据存储

- SQLite 数据库文件: `data/flight_claw.db`
- 爬虫截图: `data/screenshots/`，HTML 快照: `data/html/`，文本快照: `data/text/`
- 浏览器 profile（用于保持登录态）: `data/browser_profile/ctrip/`

### 关键设计决策

- **同步 ORM + 同步 Playwright**：爬虫任务在后台线程中运行（`threading`），不使用 FastAPI 的 async。SQLite `check_same_thread=False` 允许多线程访问
- **SQLite 迁移**：不使用 Alembic。新增字段在 `db.py:ensure_runtime_schema()` 中通过 `ALTER TABLE ADD COLUMN` 添加。部分复杂变更（如 UNIQUE 索引重构、NOT NULL → NULLABLE）通过重建表实现
- **前端路由集中管理**：所有 URL 路径在 `routes.tsx` 中统一定义，`/api` 前缀的请求被 Vite 代理到 `localhost:8000`。独立部署时通过 `VITE_API_BASE_URL` 指定后端地址
- **API 响应格式**：后端统一返回 `{"success": True, "data": ...}` 或通过 `HTTPException` 返回错误详情。前端 `request()` 自动解包 `success` 字段
- **策略枚举使用常量**：`app/constants.py` 中的常量在 `app/models.py` 作为默认值，在 `app/routers/api.py` 作为 Pydantic 正则验证模式引用
- **CORS**：仅允许 `localhost:5173` 和 `127.0.0.1:5173`，不开放跨域
