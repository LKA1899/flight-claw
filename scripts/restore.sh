#!/bin/bash
# FlightClaw - 数据恢复脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

BACKUP_DIR="${PROJECT_DIR}/backups"

if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
    echo "没有找到备份文件。备份目录: $BACKUP_DIR"
    exit 1
fi

echo "可用的备份文件:"
echo "================================================"
ls -1th "$BACKUP_DIR"/flightclaw_*.tar.gz 2>/dev/null | head -20 | while read f; do
    echo "  $(basename "$f")  ($(du -h "$f" | cut -f1))"
done
echo "================================================"
echo ""

# 如果传入了文件路径参数，直接使用
if [ -n "$1" ]; then
    BACKUP_FILE="$1"
else
    # 默认使用最新的备份
    BACKUP_FILE=$(ls -1t "$BACKUP_DIR"/flightclaw_*.tar.gz 2>/dev/null | head -1)
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

echo "将恢复: $(basename "$BACKUP_FILE")"
echo "警告: 当前数据库将被覆盖！"
read -rp "确认恢复? (输入 yes 继续): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "[1/3] 停止服务..."
docker compose down 2>/dev/null || true

echo "[2/3] 备份当前数据库 (安全起见)..."
if [ -f data/flight_claw.db ]; then
    cp data/flight_claw.db "data/flight_claw.db.before_restore_$(date +%Y%m%d_%H%M%S)"
fi

echo "[3/3] 恢复数据..."
tar -xzf "$BACKUP_FILE" -C "$PROJECT_DIR"

echo ""
echo "恢复完成。重新启动服务:"
echo "  docker compose up -d"
echo ""
echo "如果恢复后有问题，回滚:"
echo "  ls data/flight_claw.db.before_restore_*"
