#!/bin/bash
# FlightClaw - 数据备份脚本
# 备份 SQLite 数据库 + settings.json
# 截图/HTML/文本快照默认不备份（体积大），可选 --full

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

BACKUP_DIR="${PROJECT_DIR}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FULL_BACKUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full) FULL_BACKUP=true; shift ;;
        *) echo "用法: bash scripts/backup.sh [--full]"; exit 1 ;;
    esac
done

mkdir -p "$BACKUP_DIR"

if $FULL_BACKUP; then
    # 完整备份：数据库 + 配置 + 快照
    BACKUP_FILE="${BACKUP_DIR}/flightclaw_full_${TIMESTAMP}.tar.gz"
    echo "创建完整备份: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" \
        -C "$PROJECT_DIR" \
        data/flight_claw.db \
        data/settings.json \
        data/screenshots \
        data/text \
        data/html \
        data/browser_profile \
        2>/dev/null
else
    # 精简备份：仅数据库 + 配置
    BACKUP_FILE="${BACKUP_DIR}/flightclaw_${TIMESTAMP}.tar.gz"
    echo "创建精简备份: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" \
        -C "$PROJECT_DIR" \
        data/flight_claw.db \
        data/settings.json \
        2>/dev/null
fi

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "备份完成: $BACKUP_FILE ($SIZE)"

# 保留最近 30 个备份
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/flightclaw_*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 30 ]; then
    echo "清理旧备份..."
    ls -1t "$BACKUP_DIR"/flightclaw_*.tar.gz | tail -n +31 | xargs rm -f
fi

echo "当前备份数量: $(ls -1 "$BACKUP_DIR"/flightclaw_*.tar.gz 2>/dev/null | wc -l)"
