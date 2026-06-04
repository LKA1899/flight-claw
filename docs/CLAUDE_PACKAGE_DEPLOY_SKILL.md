# Claude Skill: flight-scan 部署打包

把下面内容交给 Claude，要求它在本项目中按此规则打包部署。

```text
你是 flight-scan 项目的部署打包助手。

目标：
为当前项目生成云服务器部署/更新包，并给出服务器上一条命令完成更新部署的指令。

硬性规则：

1. Docker 构建策略
   - scripts/deploy.sh 不要使用 docker compose build --pull。
   - 默认 NO_CACHE=0，使用 docker compose build，优先复用服务器本地缓存和已有镜像。
   - 如果服务器缺少基础镜像，允许 Docker build 正常拉取，不要做离线镜像检查，也不要因为缺少本地基础镜像提前报错。
   - 只有用户明确要求彻底重建时，才使用 NO_CACHE=1。

2. 常规更新包不覆盖服务器数据
   - 不包含 .env.production。
   - 不包含 data/flight_claw.db。
   - 不包含 data/settings.json，除非用户明确要求同步本地设置。
   - 不包含 data/screenshots、data/text、data/html、data/browser_profile、data/debug。
   - 数据库结构变更必须通过 app/db.py::ensure_runtime_schema() 或明确迁移逻辑完成，不要用本地数据库覆盖生产数据库。

3. 首次部署或用户明确要求“带数据库”时才打包 SQLite
   - 使用 SQLite backup API 生成一致性副本。
   - 明确提示：带数据库包会初始化或覆盖服务器数据目录中的数据库，不适合作为日常更新包。

4. 固定部署目录
   - 服务器统一部署到 /opt/flight-scan/current。
   - 使用 /opt/flight-scan/current.prev 作为上一次版本备份。
   - 不要让用户在多个时间戳目录中反复部署，避免运行旧代码。

5. 默认端口
   - docker-compose.yml 使用 ${APP_PORT:-8081}:80。
   - 部署命令默认 APP_PORT=8081。

6. Playwright/Chromium
   - Dockerfile 使用 python:3.11-slim-bookworm。
   - apt 安装系统 chromium。
   - 设置 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium。
   - 不执行 playwright install chromium --with-deps。

打包前检查：
python -m compileall app
cd frontend && npm run build
cd ..
bash -n scripts/deploy.sh
bash -n scripts/backup.sh
bash -n scripts/restore.sh

如果失败，先修复，不要打包。

常规更新包：
- 包名：flight-scan-update-YYYYMMDD_HHMMSS.tar.gz
- 包含：app、frontend 源码、nginx、scripts、docs、.claude、Dockerfile、Dockerfile.frontend、docker-compose.yml、entrypoint.sh、requirements.txt、run.py、README.md、DEPLOY_SERVER.md、.dockerignore、.env.production.example
- 排除：frontend/node_modules、frontend/dist、frontend/dist-deploy、tsconfig.tsbuildinfo、data/flight_claw.db、data/settings.json、data/screenshots、data/text、data/html、data/browser_profile、data/debug、.env.production

服务器常规更新一条命令模板：
set -e
PKG=/opt/PACKAGE_NAME.tar.gz
APP=/opt/flight-scan/current

test -f "$PKG"
rm -rf "$APP.new"
mkdir -p "$APP.new"
tar -xzf "$PKG" -C "$APP.new" --strip-components=1
test -f "$APP.new/scripts/deploy.sh"

if [ -f "$APP/.env.production" ]; then
  cp "$APP/.env.production" "$APP.new/.env.production"
elif [ -f "$APP.prev/.env.production" ]; then
  cp "$APP.prev/.env.production" "$APP.new/.env.production"
fi

if [ -d "$APP/data" ]; then
  rm -rf "$APP.new/data"
  cp -a "$APP/data" "$APP.new/data"
elif [ -d "$APP.prev/data" ]; then
  rm -rf "$APP.new/data"
  cp -a "$APP.prev/data" "$APP.new/data"
fi

rm -rf "$APP.prev"
if [ -d "$APP" ]; then mv "$APP" "$APP.prev"; fi
mv "$APP.new" "$APP"
cd "$APP"
APP_PORT=8081 NO_CACHE=0 bash scripts/deploy.sh

如果容器名冲突：
cd /opt/flight-scan/current
docker rm -f flightclaw-backend flightclaw-nginx 2>/dev/null || true
APP_PORT=8081 NO_CACHE=0 bash scripts/deploy.sh

部署后验证：
cd /opt/flight-scan/current
docker compose ps
curl -sf http://localhost:8081/api/overview
docker compose logs --tail=80 backend
docker compose logs --tail=80 nginx

最终输出必须包含：
1. 包路径
2. SHA256
3. 是否包含数据库
4. 是否会覆盖服务器数据库
5. 服务器一条命令部署指令
6. 访问地址
7. 需要放行的安全组端口
```
