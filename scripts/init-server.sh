#!/bin/bash
# FlightClaw - 初始化云服务器脚本
# 在一台全新的 Ubuntu 22.04/24.04 服务器上运行此脚本

set -e

echo "================================================"
echo " FlightClaw 服务器初始化"
echo "================================================"

# 检查是否为 root
if [ "$EUID" -ne 0 ]; then
    echo "请以 root 用户运行此脚本: sudo bash init-server.sh"
    exit 1
fi

echo ""
echo "[1/5] 更新系统包..."
apt-get update && apt-get upgrade -y

echo ""
echo "[2/5] 安装基础依赖..."
apt-get install -y \
    curl \
    wget \
    git \
    vim \
    ufw \
    htop \
    ca-certificates \
    gnupg \
    lsb-release

echo ""
echo "[3/5] 安装 Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
    echo "Docker 安装完成"
else
    echo "Docker 已安装: $(docker --version)"
fi

echo ""
echo "[4/5] 安装 Docker Compose..."
if ! command -v docker compose &> /dev/null; then
    apt-get install -y docker-compose-plugin
    echo "Docker Compose 安装完成"
else
    echo "Docker Compose 已安装"
fi

echo ""
echo "[5/5] 配置防火墙..."
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ufw status verbose

echo ""
echo "================================================"
echo " 初始化完成！"
echo "================================================"
echo ""
echo "接下来:"
echo "  1. 创建部署用户: adduser flightclaw && usermod -aG docker flightclaw"
echo "  2. 切换到部署用户: su - flightclaw"
echo "  3. 克隆项目: git clone <repo-url> && cd flight-claw"
echo "  4. 复制环境配置: cp .env.production.example .env.production"
echo "  5. 编辑配置: vim .env.production"
echo "  6. 部署: bash scripts/deploy.sh"
echo ""
