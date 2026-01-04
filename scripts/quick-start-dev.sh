#!/bin/bash
# 개발 환경 빠른 시작 스크립트
# GPU/CPU 자동 감지 및 모든 서비스 시작

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 색상 출력
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  개발 환경 빠른 시작${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

cd "$PROJECT_ROOT"

# 1. 기본 서비스 시작
echo -e "${GREEN}1단계: 기본 서비스 시작 중...${NC}"
docker compose up -d postgres redis api web
echo ""

# 2. vLLM 설정 확인 및 시작
echo -e "${GREEN}2단계: vLLM 설정 확인 중...${NC}"
if [ ! -f .env ] || ! grep -q "^VLLM_MODE=" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  vLLM 설정이 없습니다. 자동 설정을 실행합니다...${NC}"
    ./scripts/setup-dev-vllm.sh
    echo ""
fi

# 3. vLLM 시작
echo -e "${GREEN}3단계: vLLM 서버 시작 중...${NC}"
make -f Makefile.dev dev-vllm-start
echo ""

# 4. 상태 확인
echo -e "${GREEN}4단계: 서비스 상태 확인${NC}"
docker compose ps
echo ""

echo -e "${GREEN}✅ 개발 환경 시작 완료!${NC}"
echo ""
echo "접속 정보:"
echo "  - Web UI: http://localhost:3000"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "명령어:"
echo "  make -f Makefile.dev dev-status    # 전체 상태 확인"
echo "  make -f Makefile.dev dev-vllm-logs # vLLM 로그 확인"

