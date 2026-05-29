# FlightClaw 云服务器部署指南

## 一、架构概览

```
┌─────────────────────────────────────────────────────┐
│                    云服务器 (:80)                     │
│  ┌──────────────────────────────────────────────┐   │
│  │              Nginx (反向代理)                   │   │
│  │  /          → 前端静态文件 (SPA)               │   │
│  │  /api/*     → 后端 FastAPI :8000              │   │
│  └──────────────┬───────────────────────────────┘   │
│                 │                                     │
│  ┌──────────────▼───────────────────────────────┐   │
│  │           FastAPI Backend (:8000)              │   │
│  │  - SQLAlchemy + SQLite                        │   │
│  │  - APScheduler (定时扫描)                      │   │
│  │  - Playwright + Chromium (无头浏览器)          │   │
│  └──────────────┬───────────────────────────────┘   │
│                 │                                     │
│  ┌──────────────▼───────────────────────────────┐   │
│  │          持久化数据卷 (:/app/data)              │   │
│  │  - flight_claw.db (SQLite)                    │   │
│  │  - screenshots/  (截图)                        │   │
│  │  - html/  (HTML快照)                           │   │
│  │  - text/  (文本快照)                            │   │
│  │  - browser_profile/ctrip/  (浏览器登录态)       │   │
│  │  - settings.json  (运行时配置)                  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**组件说明**:

| 组件 | 技术 | 端口 | 说明 |
|------|------|------|------|
| Nginx | nginx:alpine | 80 | 反向代理 + 前端静态文件 |
| Backend | Python 3.11 + FastAPI | 8000 (内部) | API + Playwright 扫描 |
| SQLite | 文件存储 | - | 单文件，不需要独立进程 |
| Scheduler | APScheduler | - | 运行在 Backend 进程内 |

**关键约束**:
- 扫描为低频、串行操作（Playwright 全局锁 `_browser_lock`）
- SQLite 依赖 `check_same_thread=False` 允许多线程
- 不做高并发设计

---

## 二、服务器要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Ubuntu 22.04 / 24.04 | Ubuntu 24.04 LTS |
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 磁盘 | 20 GB | 40 GB+ |
| 网络 | 公网 IP | 公网 IP + 域名 |

**软件依赖**: Docker 24+, Docker Compose v2

---

## 三、部署步骤

### 3.1 服务器初始化 (全新服务器)

```bash
# SSH 登录服务器
ssh root@YOUR_SERVER_IP

# 如果项目已通过 git clone 获取，直接运行初始化脚本
cd flight-claw
sudo bash scripts/init-server.sh
```

如果还没有克隆项目：

```bash
# 先安装 git
apt-get update && apt-get install -y git

# 克隆项目
git clone <YOUR_REPO_URL> flight-claw
cd flight-claw
sudo bash scripts/init-server.sh
```

初始化脚本会自动安装 Docker、Docker Compose，并配置防火墙。

### 3.2 创建部署用户 (推荐)

```bash
adduser flightclaw
usermod -aG docker flightclaw
su - flightclaw
cd ~/flight-claw  # 或重新 clone
```

### 3.3 配置环境变量

```bash
cp .env.production.example .env.production
vim .env.production
```

最小配置（不填也能运行，但会跳过管理员初始化）:

```ini
# 管理员账号 (首次部署必须配置)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<your-strong-password>
SECRET_KEY=<random-string>

# LLM 报告分析 (可选)
OPENAI_BASE_URL=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

# 通知 (可选)
PUSHPLUS_TOKEN=
WEWORK_WEBHOOK_URL=
```

### 3.4 迁移本地数据 (可选)

如果本地已有数据库和浏览器登录态，先迁移到服务器：

```bash
# 本地：打包数据库 + 浏览器 Profile
cd flight-claw
tar -czf data-migration.tar.gz \
  data/flight_claw.db \
  data/settings.json \
  data/browser_profile/ctrip/

# 上传到服务器
scp data-migration.tar.gz user@YOUR_SERVER_IP:~/flight-claw/

# 服务器：解压
ssh user@YOUR_SERVER_IP
cd ~/flight-claw
docker compose down 2>/dev/null || true
tar -xzf data-migration.tar.gz
```

浏览器 Profile (`data/browser_profile/ctrip/`) 包含了携程登录态，迁移后无需重新登录。

### 3.5 部署启动

```bash
bash scripts/deploy.sh
```

部署脚本会:
1. 创建数据目录
2. 构建 Docker 镜像（前端 + 后端）
3. 启动所有容器
4. 验证服务健康状态

### 3.6 验证部署

```bash
# 检查容器状态
docker compose ps

# 查看日志
docker compose logs -f

# API 健康检查
curl http://localhost/api/overview
```

浏览器访问 `http://YOUR_SERVER_IP` 即可进入前端页面。

---

## 四、配置说明

### 4.1 环境变量 (`.env.production`)

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_BASE_URL` | 否 | `https://api.openai.com/v1` | LLM API 地址 |
| `OPENAI_API_KEY` | 否 | - | LLM API Key |
| `OPENAI_MODEL` | 否 | `gpt-4o-mini` | LLM 模型名称 |
| `PUSHPLUS_TOKEN` | 否 | - | PushPlus 通知 Token |
| `WEWORK_WEBHOOK_URL` | 否 | - | 企业微信 Webhook URL |
| `CORS_ORIGINS` | 否 | `http://localhost:5173,...` | 额外 CORS 来源（逗号分隔） |
| `SECRET_KEY` | **是** | - | JWT 签名密钥（生产环境必须修改） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 否 | `1440` | JWT 过期时间（分钟，默认 24h） |
| `ADMIN_USERNAME` | 否 | `admin` | 默认管理员用户名 |
| `ADMIN_PASSWORD` | **是** | - | 默认管理员初始密码（仅首次启动使用） |

### 4.2 运行时设置

`data/settings.json`（容器自动创建）:

```json
{"headless": true}
```

通过前端 **设置页面** (`/settings`) 修改，或直接编辑 JSON 文件后重启容器。

### 4.4 登录说明

**首次登录**:

1. 在 `.env.production` 中配置 `ADMIN_USERNAME`、`ADMIN_PASSWORD`、`SECRET_KEY`
2. 首次启动时，系统自动创建管理员用户（密码使用 bcrypt 加密存储）
3. 已存在用户时不会覆盖密码，修改 `.env.production` 中的 `ADMIN_PASSWORD` 不会影响已有用户
4. 浏览器访问 `http://YOUR_SERVER_IP` 自动跳转到登录页
5. 输入用户名、密码和图形验证码完成登录
6. 登录后 Token 有效期 24 小时（可配置 `ACCESS_TOKEN_EXPIRE_MINUTES`）

**安全建议**:

- 生产环境必须修改 `SECRET_KEY` 和 `ADMIN_PASSWORD`
- `SECRET_KEY` 建议使用 `openssl rand -hex 32` 生成随机字符串
- 当前版本不支持页面修改密码，后续版本提供

**修改管理员密码**:

如需修改已创建的管理员密码，可运行：

```bash
docker exec -it flightclaw-backend python -c "
from app.db import SessionLocal
from app.models import FlightUser
from app.security.password import hash_password
from sqlalchemy import select

db = SessionLocal()
user = db.scalar(select(FlightUser).where(FlightUser.username == 'admin'))
if user:
    user.password_hash = hash_password('new-password')
    db.commit()
    print('Password updated')
else:
    print('User not found')
db.close()
"
```

### 4.3 Headless 模式

云端部署时 `headless` 默认为 `true`（无头浏览器模式）。
如需远程调试或有验证码需要人工处理，可以通过前端设置页面切换为 `false`（需要 VNC 等远程桌面方案配合）。

---

## 五、运维操作

### 5.1 查看日志

```bash
# 所有服务
docker compose logs -f

# 仅后端
docker compose logs -f backend

# 仅 Nginx
docker compose logs -f nginx

# 最近 100 行
docker compose logs --tail=100 backend
```

### 5.2 重启服务

```bash
docker compose restart
```

### 5.3 停止服务

```bash
docker compose down
```

### 5.4 更新部署

```bash
git pull
bash scripts/deploy.sh
```

### 5.5 备份数据

```bash
# 精简备份（数据库 + 配置，推荐日常使用）
bash scripts/backup.sh

# 完整备份（含截图和 HTML 快照）
bash scripts/backup.sh --full
```

备份文件存储在 `backups/` 目录，自动保留最近 30 个。

**设置 crontab 自动备份**:

```bash
crontab -e
# 每天凌晨 2 点备份
0 2 * * * cd /home/flightclaw/flight-claw && bash scripts/backup.sh >> backups/cron.log 2>&1
```

### 5.6 恢复数据

```bash
bash scripts/restore.sh
```

脚本会列出可用备份，确认后自动恢复并提示重启。

---

## 六、持久化说明

以下目录通过 bind mount 挂载到宿主机，容器重建不丢数据：

```
./data:/app/data
```

| 路径 | 内容 | 说明 |
|------|------|------|
| `data/flight_claw.db` | SQLite 数据库 | **核心数据** — Monitor、Scan、Price、Plan 等所有记录 |
| `data/settings.json` | 运行时设置 | headless 开关等 |
| `data/screenshots/` | 浏览器截图 | 每次扫描的航班列表截图 |
| `data/html/` | HTML 快照 | 航班搜索结果页完整 HTML |
| `data/text/` | 文本快照 | 提取的可见文本 |
| `data/browser_profile/ctrip/` | 浏览器 Profile | **登录态保持** — 删除后需要重新登录携程 |
| `data/debug/` | 调试文件 | 可选 |

---

## 七、配置 HTTPS (可选)

使用 Let's Encrypt + Certbot:

```bash
# 安装 certbot
sudo apt-get install -y certbot

# 先停止 Nginx
docker compose stop nginx

# 获取证书 (standalone 模式)
sudo certbot certonly --standalone -d your-domain.com

# 证书路径
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

修改 `nginx/nginx.conf`，添加 HTTPS server block，然后重新构建:

```bash
docker compose up -d --build nginx
```

---

## 八、人工接管 / 远程登录

当携程要求登录或验证码时，需要人工接管浏览器。有两种方案：

### 方案 A: 使用持久化 Browser Profile (推荐)

1. 在本地开发环境，启动项目并手动登录携程
2. 将本地 `data/browser_profile/ctrip/` 目录打包上传到服务器
3. 恢复 profile 后重启容器

```bash
# 本地打包
tar -czf profile.tar.gz -C data browser_profile/ctrip

# 上传服务器
scp profile.tar.gz user@server:~/flight-claw/

# 服务器解压
cd ~/flight-claw
tar -xzf profile.tar.gz
docker compose restart backend
```

### 方案 B: VNC 远程桌面

1. 在服务器上安装桌面环境和 VNC
2. 临时关闭 headless 模式（通过设置页面）
3. VNC 连接到服务器，手动操作浏览器
4. 完成后恢复 headless 模式

---

## 九、常见问题

### Q: 容器启动后前端正常但 API 请求失败

```bash
# 检查 backend 容器状态
docker compose ps backend

# 查看 backend 日志
docker compose logs backend
```

常见原因:
- `data/settings.json` 权限不对 → 删除后重启
- SQLite 数据库损坏 → 从备份恢复

### Q: Playwright 启动失败

```bash
# 进入容器检查
docker exec -it flightclaw-backend playwright install --dry-run chromium
```

如果缺少系统依赖:
```bash
docker exec -it flightclaw-backend playwright install chromium --with-deps
```

### Q: 扫描时浏览器超时

健康检查 `/api/overview` 看后端是否正常。如果超时偶发，可能是携程页面加载慢，属于正常波动。

### Q: 修改前端代码后不生效

需要重新构建 nginx 镜像:
```bash
docker compose up -d --build nginx
```

### Q: 磁盘空间不足

```bash
# 查看占用
du -sh data/screenshots data/html data/text

# 清理旧快照
find data/screenshots -name "*.png" -mtime +30 -delete
find data/html -name "*.html" -mtime +30 -delete
find data/text -name "*.txt" -mtime +30 -delete
```

---

## 十、目录结构总览

```
flight-claw/
├── app/                       # 后端代码
├── frontend/                  # 前端代码
├── nginx/
│   └── nginx.conf             # Nginx 反向代理配置
├── scripts/
│   ├── init-server.sh         # 服务器初始化
│   ├── deploy.sh              # 部署/更新
│   ├── backup.sh              # 数据备份
│   └── restore.sh             # 数据恢复
├── data/                      # 持久化数据 (挂载到容器)
│   ├── flight_claw.db
│   ├── settings.json
│   ├── screenshots/
│   ├── text/
│   ├── html/
│   ├── browser_profile/
│   └── debug/
├── Dockerfile                 # 后端镜像
├── Dockerfile.frontend        # 前端 + Nginx 镜像
├── docker-compose.yml         # 服务编排
├── entrypoint.sh              # 容器启动脚本
├── .env.production            # 生产环境变量 (不提交 git)
├── .env.production.example    # 环境变量示例
├── .dockerignore              # Docker 构建排除文件
├── requirements.txt           # Python 依赖
└── run.py                     # 本地开发入口
```
