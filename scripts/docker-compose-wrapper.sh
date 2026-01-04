#!/bin/bash
# docker compose 명령어 wrapper
# docker compose up 실행 전 자동으로 GPU/CPU 감지 및 설정

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# docker compose up 또는 up 명령어인 경우에만 자동 감지 실행
if [ "$1" = "up" ] || [ "$1" = "start" ]; then
    echo "🔍 vLLM 설정 자동 감지 중..."
    "$SCRIPT_DIR/auto-detect-vllm.sh" || true
    echo ""
fi

# 원래 docker compose 명령어 실행
exec docker compose "$@"

