# flight-scan 云服务器部署

## 服务器要求

- Ubuntu 22.04/24.04
- Docker 与 Docker Compose 插件
- 80 端口开放

## 上传部署包

将 `flight-scan-deploy-*.tar.gz` 上传到服务器后执行：

```bash
mkdir -p ~/flight-scan
tar -xzf flight-scan-deploy-*.tar.gz -C ~/flight-scan
cd ~/flight-scan
```

## 首次启动

```bash
bash scripts/deploy.sh
```

启动后检查：

```bash
docker compose ps
curl -sf http://localhost/api/overview
docker compose logs -f backend
```

## 数据说明

- SQLite 数据库位于 `data/flight_claw.db`
- 运行配置位于 `data/settings.json`
- 容器通过 `./data:/app/data` 挂载，重建镜像不会删除数据库

## 登录说明

当前部署包包含 `.env.production` 和数据库中的初始管理员。上线后请尽快修改 `.env.production` 中的 `SECRET_KEY` 和管理员密码策略，并避免将部署包公开传播。

## 常用命令

```bash
docker compose up -d
docker compose down
docker compose logs -f
bash scripts/backup.sh
```
