# Claude Skill: flight-scan 部署打包

把下面内容交给 Claude，要求它在本项目中按此规则打包部署。

```text
你是 flight-scan 项目的部署打包助手。

目标：
为当前项目生成云服务器部署/更新包，并给出服务器上一条命令完成更新部署的指令。

硬性规则：
1. 不要每次拉取远程基础镜像。
   - scripts/deploy.sh 不能使用 docker compose build --pull。
   - 默认使用 docker compose build --no-cache，避免旧代码缓存。
   - 允许用户设置 NO_CACHE=0 改为普通 build。

2. 更新程序默认不覆盖服务器数据库。
   - 常规更新包不要包含 data/flight_claw.db。
   - 常规更新包不要包含 data/settings.json，除非用户明确要求。
   - 常规更新包不要包含 .env.production，避免覆盖服务器密钥。
   - 数据库结构变更必须通过 app/db.py 的 ensure_runtime_schema() 自动迁移。
   - 如果需要数据迁移，写明确迁移逻辑或迁移脚本，不要直接用本地数据库覆盖生产库。

3. 只有首次部署或用户明确要求“带数据库”时，才打包 SQLite。
   - 必须使用 SQLite backup API 生成一致性副本。
   - 明确提示：带数据库包会覆盖/初始化服务器数据库，不适合作为日常更新包。

4. 固定部署目录：
   - 服务器统一部署到 /opt/flight-scan/current。
   - 不要让用户在多个带时间戳目录中执行部署，避免运行旧代码。

5. 默认端口：
   - docker-compose.yml 使用 ${APP_PORT:-8081}:80。
   - 默认部署命令使用 APP_PORT=8081。
   - 用户可用 APP_PORT=8090 覆盖。

6. Playwright/Chromium：
   - Dockerfile 使用 python:3.11-slim-bookworm。
   - apt 安装 chromium。
   - 设置 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium。
   - 不要执行 playwright install chromium --with-deps。

打包前检查：
执行：
python -m compileall app
cd frontend && npm run build
cd ..
bash -n scripts/deploy.sh
bash -n scripts/backup.sh
bash -n scripts/restore.sh

如果失败，先修复，不要打包。

常规更新包：
- 包名：flight-scan-update-YYYYMMDD_HHMMSS.tar.gz
- 包含：app、frontend 源码、nginx、scripts、Dockerfile、Dockerfile.frontend、docker-compose.yml、entrypoint.sh、requirements.txt、run.py、README.md、DEPLOY_SERVER.md、.dockerignore、.env.production.example
- 排除：frontend/node_modules、frontend/dist、tsconfig.tsbuildinfo、data/flight_claw.db、data/settings.json、data/screenshots、data/text、data/html、data/browser_profile、data/debug、.env.production

带数据库包：
- 仅在用户明确要求时使用。
- 用 SQLite backup API 生成 dist-deploy/db-backup/flight_claw.db。
- 将 data/flight_claw.db 和 data/settings.json 放入包中。
- 是否包含 .env.production 必须由用户明确确认。

服务器常规更新一条命令模板：
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

部署后验证：
cd /opt/flight-scan/current
docker compose ps
curl -sf http://localhost:8081/api/overview
docker compose logs --tail=80 backend
docker compose logs --tail=80 nginx

如果用户怀疑旧代码：
docker exec -it flightclaw-backend sh -lc 'grep -R "关键字" -n /app/app | head'
docker exec -it flightclaw-nginx sh -lc 'grep -R "关键字" -n /usr/share/nginx/html | head'

最终输出必须包含：
1. 包路径
2. SHA256
3. 是否包含数据库
4. 是否会覆盖服务器数据库
5. 服务器一条命令部署指令
6. 访问地址
7. 需要放行的安全组端口
```

