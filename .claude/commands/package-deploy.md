# package-deploy

为 flight-scan 生成云服务器部署/更新包。这个命令用于把当前项目代码打成可上传服务器的 `.tar.gz`，并给出服务器上一条命令完成更新部署的指令。

## 核心原则

1. 不要每次拉取远程基础镜像。
   - `scripts/deploy.sh` 必须使用 `docker compose build`。
   - 不要使用 `docker compose build --pull`。
   - 默认允许 `--no-cache` 重建应用层，避免旧代码缓存。

2. 更新部署默认不覆盖服务器数据库。
   - 常规更新包不要包含 `data/flight_claw.db`。
   - 常规更新包不要包含 `data/settings.json`，除非用户明确要求同步本地设置。
   - 数据库结构变更应通过 `app/db.py::ensure_runtime_schema()` 自动迁移。
   - 如果必须迁移数据，新增明确的迁移逻辑或脚本，不能直接用本地数据库覆盖生产库。

3. 首次部署或用户明确要求“带数据库”时才打包 SQLite。
   - 使用 SQLite backup API 生成一致性副本，不能直接压缩正在使用的 `data/flight_claw.db`。
   - 明确告诉用户：带数据库的包会覆盖/初始化服务器数据目录中的数据库。

4. 部署目录固定。
   - 服务器固定使用 `/opt/flight-scan/current`。
   - 不要让用户在多个带时间戳目录里反复部署，避免部署错旧目录。

5. 默认端口避开 80。
   - `docker-compose.yml` 使用 `${APP_PORT:-8081}:80`。
   - 部署命令默认 `APP_PORT=8081`。
   - 如果用户要换端口，允许 `APP_PORT=8090` 之类覆盖。

6. Playwright 不下载自带 Chromium。
   - Dockerfile 使用 `python:3.11-slim-bookworm`。
   - apt 安装系统 `chromium`。
   - 设置 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium`。
   - 不要执行 `playwright install chromium --with-deps`，国内镜像可能缺 `chromium-headless-shell`。

## 打包前检查

先检查以下文件是否满足部署约束：

```bash
grep -n -- '--pull' scripts/deploy.sh || true
grep -n 'APP_PORT' docker-compose.yml scripts/deploy.sh
grep -n 'PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH\|playwright install' Dockerfile app/crawler/ctrip.py
```

要求：

- `scripts/deploy.sh` 不能出现 `--pull`。
- `docker-compose.yml` 端口应为 `${APP_PORT:-8081}:80`。
- `Dockerfile` 不能再有 `RUN playwright install chromium --with-deps`。
- `app/crawler/ctrip.py` 需要把环境变量传给 `launch_persistent_context(executable_path=...)`。

## 验证命令

每次打包前必须执行：

```bash
python -m compileall app
cd frontend && npm run build
cd ..
bash -n scripts/deploy.sh
bash -n scripts/backup.sh
bash -n scripts/restore.sh
```

如果任一命令失败，停止打包并先修复。

## 常规更新包，不带数据库

默认使用这个模式。适用于修 bug、改前端、改后端、改数据库模型但由 `ensure_runtime_schema()` 自动迁移的情况。

PowerShell 打包参考：

```powershell
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$outDir = Join-Path (Get-Location) 'dist-deploy'
$stage = Join-Path $outDir "flight-scan-update-$stamp"
$pkg = Join-Path $outDir "flight-scan-update-$stamp.tar.gz"

if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force -Path $stage | Out-Null

Copy-Item app,nginx,scripts -Destination $stage -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $stage 'frontend') | Out-Null
robocopy frontend (Join-Path $stage 'frontend') /E /XD node_modules dist /XF tsconfig.tsbuildinfo | Out-Null

Copy-Item Dockerfile,Dockerfile.frontend,docker-compose.yml,entrypoint.sh,requirements.txt,run.py,README.md,DEPLOY_SERVER.md,.dockerignore,.env.production.example -Destination $stage -Force

tar -czf $pkg -C $outDir "flight-scan-update-$stamp"
Remove-Item -Recurse -Force $stage
Get-Item $pkg | Select-Object FullName,Length,LastWriteTime
Get-FileHash $pkg -Algorithm SHA256 | Format-List
```

注意：常规更新包不包含 `.env.production`，避免覆盖服务器生产密钥。

## 首次部署包或显式带数据库包

只有用户明确要求“带数据库一起部署/初始化”时使用。

先用 SQLite backup API 备份数据库：

```powershell
@'
import sqlite3
from pathlib import Path
src = Path('data/flight_claw.db')
dst_dir = Path('dist-deploy/db-backup')
dst_dir.mkdir(parents=True, exist_ok=True)
dst = dst_dir / 'flight_claw.db'
source = sqlite3.connect(src)
target = sqlite3.connect(dst)
source.backup(target)
target.close()
source.close()
print(dst.resolve())
print(dst.stat().st_size)
'@ | python -
```

然后在 staging 目录中加入：

- `data/flight_claw.db`
- `data/settings.json`
- `.env.production`，仅在用户明确要求连生产配置一起带上时加入

必须在最终回复中提醒：带数据库包会覆盖/初始化服务器数据库，不适合作为常规更新包。

## 服务器一条命令部署

常规更新包部署命令模板：

```bash
rm -rf /opt/flight-scan/current.new \
&& mkdir -p /opt/flight-scan/current.new \
&& tar -xzf /root/PACKAGE_NAME.tar.gz -C /opt/flight-scan/current.new --strip-components=1 \
&& cp -n /opt/flight-scan/current/.env.production /opt/flight-scan/current.new/.env.production 2>/dev/null || true \
&& cp -rn /opt/flight-scan/current/data /opt/flight-scan/current.new/data 2>/dev/null || true \
&& rm -rf /opt/flight-scan/current.prev \
&& mv /opt/flight-scan/current /opt/flight-scan/current.prev 2>/dev/null || true \
&& mv /opt/flight-scan/current.new /opt/flight-scan/current \
&& cd /opt/flight-scan/current \
&& APP_PORT=8081 NO_CACHE=1 bash scripts/deploy.sh
```

如果这是首次部署且包内已经包含 `.env.production` 和 `data/flight_claw.db`，可以简化为：

```bash
rm -rf /opt/flight-scan/current \
&& mkdir -p /opt/flight-scan/current \
&& tar -xzf /root/PACKAGE_NAME.tar.gz -C /opt/flight-scan/current --strip-components=1 \
&& cd /opt/flight-scan/current \
&& APP_PORT=8081 NO_CACHE=1 bash scripts/deploy.sh
```

## 部署后验证

给用户这些命令：

```bash
cd /opt/flight-scan/current
docker compose ps
curl -sf http://localhost:8081/api/overview
docker compose logs --tail=80 backend
docker compose logs --tail=80 nginx
```

如果用户怀疑仍是旧代码，让用户查容器内源码或前端产物：

```bash
docker exec -it flightclaw-backend sh -lc 'grep -R "关键字" -n /app/app | head'
docker exec -it flightclaw-nginx sh -lc 'grep -R "关键字" -n /usr/share/nginx/html | head'
```

## 最终回复格式

打包完成后输出：

1. 包路径
2. SHA256
3. 是否包含数据库
4. 是否会覆盖服务器数据库
5. 服务器一条命令部署指令
6. 访问地址，例如 `http://服务器IP:8081`
7. 需要放行的安全组端口

