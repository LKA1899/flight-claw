# flight-scan

flight-scan 是一个个人机票监控工具。当前用户界面只保留 React 前端，访问入口是：

```text
http://127.0.0.1:5173
```

FastAPI 后端只作为 JSON API 服务使用，供前端通过 `/api` 代理调用；不再提供 `http://127.0.0.1:8000` 下的服务端页面。

## 技术栈

- Python 3.11+
- FastAPI
- SQLite
- SQLAlchemy
- React + Vite + TypeScript
- Tailwind CSS + Radix UI 风格组件
- Playwright
- APScheduler

## 安装

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

cd frontend
npm install
```

## 启动

先启动 API 后端：

```bash
python run.py
```

再启动前端：

```bash
cd frontend
npm run dev
```

打开：

```text
http://127.0.0.1:5173
```

Vite 开发服务器配置了 `/api -> http://localhost:8000` 代理；也可以通过 `frontend/.env.example` 配置 `VITE_API_BASE_URL`。

## 当前使用流程

1. 在“关注路线”中新建或维护路线。
2. 在维护路线页面中维护日期。
3. 点击路线的“立即扫描”，或在路线级“定时扫描”中配置周期扫描。
4. 在“扫描记录”查看执行进度。
5. 在“查询任务”“价格快照”“候选方案”“往返结果”“今日机会”和“旅行报告”中查看结果。

## 说明

- 后端不再挂载 Jinja2 模板、Bootstrap 静态资源或服务端控制台路由。
- workflow 页面、workflow API、workflow 调度和 workflow 执行引擎已移除。
- 数据库中历史版本遗留的字段或表不会在启动时强制删除，以避免破坏已有 SQLite 数据；当前运行路径不再使用这些入口。
