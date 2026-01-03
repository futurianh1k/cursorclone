#!/bin/bash
# ============================================================
# deploy-offline.sh
# 오프라인(에어갭) 환경에서 서비스 배포 스크립트
# ============================================================
# 사용법: ./scripts/deploy-offline.sh [COMMAND]
#
# 명령어:
#   load-images     Docker 이미지 로드
#   setup-models    LLM 모델 설정
#   configure       환경 설정
#   start           서비스 시작
#   stop            서비스 중지
#   status          서비스 상태 확인
#   verify          배포 검증
#   all             전체 배포 (load-images → setup-models → configure → start → verify)
#
# 예시:
#   ./scripts/deploy-offline.sh all
#   ./scripts/deploy-offline.sh start
#
# 출처: Opus 프로젝트 리뷰 권장사항 (2026-01-03)
# ============================================================

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 기본 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
IMAGES_DIR="${PROJECT_ROOT}/images"
MODELS_DIR="/models"

# 로깅 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Docker 이미지 로드
load_images() {
    log_info "Docker 이미지 로드 중..."
    
    if [[ ! -d "$IMAGES_DIR" ]]; then
        log_error "이미지 디렉토리를 찾을 수 없습니다: $IMAGES_DIR"
        log_info "prepare-offline.sh로 생성한 패키지에서 images/ 폴더를 복사하세요."
        exit 1
    fi
    
    for tar_file in "$IMAGES_DIR"/*.tar; do
        if [[ -f "$tar_file" ]]; then
            log_info "로드 중: $(basename "$tar_file")"
            docker load -i "$tar_file"
            log_success "로드 완료: $(basename "$tar_file")"
        fi
    done
    
    log_success "모든 Docker 이미지 로드 완료"
    echo ""
    docker images
}

# LLM 모델 설정
setup_models() {
    log_info "LLM 모델 설정 중..."
    
    # 모델 디렉토리 확인
    if [[ ! -d "${PROJECT_ROOT}/models" ]]; then
        log_error "모델 디렉토리를 찾을 수 없습니다: ${PROJECT_ROOT}/models"
        exit 1
    fi
    
    # 시스템 모델 디렉토리 생성
    sudo mkdir -p "$MODELS_DIR"
    
    # 모델 복사
    log_info "모델 복사 중 (시간이 걸릴 수 있습니다)..."
    sudo cp -r "${PROJECT_ROOT}/models"/* "$MODELS_DIR/"
    
    # 권한 설정
    sudo chmod -R 755 "$MODELS_DIR"
    
    log_success "LLM 모델 설정 완료"
    echo ""
    ls -la "$MODELS_DIR"
}

# 환경 설정
configure() {
    log_info "환경 설정 중..."
    
    cd "$PROJECT_ROOT"
    
    # .env 파일 생성
    if [[ -f ".env" ]]; then
        log_warn ".env 파일이 이미 존재합니다."
        read -p "덮어쓰시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info ".env 파일 유지"
            return
        fi
    fi
    
    if [[ -f ".env.offline" ]]; then
        cp .env.offline .env
        log_info ".env.offline을 .env로 복사했습니다."
    elif [[ -f ".env.example" ]]; then
        cp .env.example .env
        log_info ".env.example을 .env로 복사했습니다."
    else
        log_error ".env 템플릿을 찾을 수 없습니다."
        exit 1
    fi
    
    log_warn "⚠️ .env 파일의 비밀번호와 시크릿 키를 반드시 변경하세요!"
    log_info "편집: nano .env"
    
    log_success "환경 설정 완료"
}

# 서비스 시작
start_services() {
    log_info "서비스 시작 중..."
    
    cd "$PROJECT_ROOT"
    
    # 기본 서비스 시작
    docker compose up -d
    
    # vLLM 서비스 시작 (별도 compose 파일이 있는 경우)
    if [[ -f "docker-compose.vllm.yml" ]]; then
        log_info "vLLM 서비스 시작 중..."
        docker compose -f docker-compose.vllm.yml up -d
    fi
    
    # WebIDE 서비스 시작 (별도 compose 파일이 있는 경우)
    if [[ -f "docker-compose.webide.yml" ]]; then
        log_info "WebIDE 서비스 시작 중..."
        docker compose -f docker-compose.webide.yml up -d
    fi
    
    log_success "서비스 시작 완료"
    
    # 상태 확인
    sleep 5
    show_status
}

# 서비스 중지
stop_services() {
    log_info "서비스 중지 중..."
    
    cd "$PROJECT_ROOT"
    
    docker compose down
    
    if [[ -f "docker-compose.vllm.yml" ]]; then
        docker compose -f docker-compose.vllm.yml down
    fi
    
    if [[ -f "docker-compose.webide.yml" ]]; then
        docker compose -f docker-compose.webide.yml down
    fi
    
    log_success "서비스 중지 완료"
}

# 서비스 상태 확인
show_status() {
    log_info "서비스 상태 확인 중..."
    echo ""
    docker compose ps
    echo ""
}

# 배포 검증
verify_deployment() {
    log_info "배포 검증 중..."
    echo ""
    
    local all_passed=true
    
    # 1. 외부 연결 차단 확인
    log_info "1. 외부 네트워크 격리 확인..."
    if curl -s --connect-timeout 3 https://google.com > /dev/null 2>&1; then
        log_warn "⚠️ 외부 인터넷에 연결 가능합니다. 에어갭 환경이 아닙니다."
    else
        log_success "✅ 외부 인터넷 연결 차단됨"
    fi
    echo ""
    
    # 2. API 서버 확인
    log_info "2. API 서버 확인..."
    if curl -s http://localhost:8000/health | grep -q "ok"; then
        log_success "✅ API 서버 정상"
    else
        log_error "❌ API 서버 응답 없음"
        all_passed=false
    fi
    echo ""
    
    # 3. 웹 서버 확인
    log_info "3. 웹 서버 확인..."
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
        log_success "✅ 웹 서버 정상"
    else
        log_warn "⚠️ 웹 서버 응답 확인 필요"
    fi
    echo ""
    
    # 4. vLLM 서버 확인
    log_info "4. vLLM 서버 확인..."
    if curl -s http://localhost:8001/health 2>/dev/null | grep -q "ok"; then
        log_success "✅ vLLM 서버 정상"
    elif curl -s http://localhost:8001/v1/models 2>/dev/null | grep -q "data"; then
        log_success "✅ vLLM 서버 정상"
    else
        log_warn "⚠️ vLLM 서버 확인 필요 (GPU 로드 중일 수 있음)"
    fi
    echo ""
    
    # 5. 데이터베이스 확인
    log_info "5. 데이터베이스 확인..."
    if docker exec cursor-poc-db pg_isready -U cursor > /dev/null 2>&1; then
        log_success "✅ PostgreSQL 정상"
    else
        log_error "❌ PostgreSQL 응답 없음"
        all_passed=false
    fi
    echo ""
    
    # 6. Redis 확인
    log_info "6. Redis 확인..."
    if docker exec cursor-poc-redis redis-cli ping | grep -q "PONG"; then
        log_success "✅ Redis 정상"
    else
        log_error "❌ Redis 응답 없음"
        all_passed=false
    fi
    echo ""
    
    # 최종 결과
    echo "============================================"
    if $all_passed; then
        log_success "🎉 배포 검증 완료! 모든 서비스가 정상입니다."
    else
        log_error "❌ 일부 서비스에 문제가 있습니다. 로그를 확인하세요."
        log_info "로그 확인: docker compose logs -f"
    fi
    echo "============================================"
    echo ""
    log_info "웹 UI 접속: http://localhost:3000"
    log_info "API 문서: http://localhost:8000/docs"
}

# 전체 배포
deploy_all() {
    log_info "전체 배포 시작..."
    echo ""
    
    load_images
    setup_models
    configure
    start_services
    
    log_info "서비스 초기화 대기 중 (30초)..."
    sleep 30
    
    verify_deployment
}

# 도움말
show_help() {
    head -22 "$0" | tail -17
    exit 0
}

# 메인
main() {
    local command="${1:-help}"
    
    case $command in
        load-images)
            load_images
            ;;
        setup-models)
            setup_models
            ;;
        configure)
            configure
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        status)
            show_status
            ;;
        verify)
            verify_deployment
            ;;
        all)
            deploy_all
            ;;
        -h|--help|help)
            show_help
            ;;
        *)
            log_error "알 수 없는 명령어: $command"
            show_help
            ;;
    esac
}

main "$@"
