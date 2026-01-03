#!/bin/bash
# ============================================================
# prepare-offline.sh
# 오프라인(에어갭) 환경 배포를 위한 패키지 준비 스크립트
# ============================================================
# 사용법: ./scripts/prepare-offline.sh [OPTIONS]
#
# 옵션:
#   --model-size    : 모델 크기 (small|medium|large) [기본: medium]
#   --output-dir    : 출력 디렉토리 [기본: ./offline-package]
#   --skip-models   : 모델 다운로드 건너뛰기
#   --skip-images   : Docker 이미지 저장 건너뛰기
#   -h, --help      : 도움말 표시
#
# 예시:
#   ./scripts/prepare-offline.sh --model-size large --output-dir /mnt/usb
#
# 출처: Opus 프로젝트 리뷰 권장사항 (2026-01-03)
# ============================================================

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본값
MODEL_SIZE="medium"
OUTPUT_DIR="./offline-package"
SKIP_MODELS=false
SKIP_IMAGES=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 로깅 함수
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 도움말
show_help() {
    head -25 "$0" | tail -20
    exit 0
}

# 인자 파싱
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --model-size)
                MODEL_SIZE="$2"
                shift 2
                ;;
            --output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --skip-models)
                SKIP_MODELS=true
                shift
                ;;
            --skip-images)
                SKIP_IMAGES=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done
}

# 모델 크기에 따른 모델 선택
get_model_name() {
    case $MODEL_SIZE in
        small)
            echo "Qwen/Qwen2.5-Coder-1.5B-Instruct"
            ;;
        medium)
            echo "Qwen/Qwen2.5-Coder-7B-Instruct"
            ;;
        large)
            echo "Qwen/Qwen2.5-Coder-14B-Instruct"
            ;;
        xlarge)
            echo "Qwen/Qwen2.5-Coder-32B-Instruct"
            ;;
        *)
            log_error "Invalid model size: $MODEL_SIZE"
            log_info "Valid options: small, medium, large, xlarge"
            exit 1
            ;;
    esac
}

# 필수 도구 확인
check_requirements() {
    log_info "필수 도구 확인 중..."
    
    local missing=()
    
    if ! command -v docker &> /dev/null; then
        missing+=("docker")
    fi
    
    if ! command -v huggingface-cli &> /dev/null; then
        if ! $SKIP_MODELS; then
            log_warn "huggingface-cli가 설치되지 않았습니다. 설치합니다..."
            pip install -q huggingface-hub
        fi
    fi
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        log_error "다음 도구가 필요합니다: ${missing[*]}"
        exit 1
    fi
    
    log_success "필수 도구 확인 완료"
}

# 디렉토리 생성
create_directories() {
    log_info "디렉토리 구조 생성 중..."
    
    mkdir -p "$OUTPUT_DIR/images"
    mkdir -p "$OUTPUT_DIR/models"
    mkdir -p "$OUTPUT_DIR/source"
    
    log_success "디렉토리 생성 완료: $OUTPUT_DIR"
}

# Docker 이미지 다운로드 및 저장
save_docker_images() {
    if $SKIP_IMAGES; then
        log_warn "Docker 이미지 저장 건너뛰기"
        return
    fi
    
    log_info "Docker 이미지 다운로드 및 저장 중..."
    
    # 필수 이미지 목록
    local images=(
        "vllm/vllm-openai:latest"
        "postgres:15-alpine"
        "redis:7-alpine"
        "nginx:1.25-alpine"
        "gitea/gitea:1.21-rootless"
        "ghcr.io/berriai/litellm:main-latest"
        "quay.io/keycloak/keycloak:23.0"
    )
    
    for image in "${images[@]}"; do
        local image_name=$(echo "$image" | tr '/:' '_')
        local tar_file="$OUTPUT_DIR/images/${image_name}.tar"
        
        if [[ -f "$tar_file" ]]; then
            log_warn "이미지 이미 존재: $image_name.tar"
            continue
        fi
        
        log_info "다운로드 중: $image"
        docker pull "$image" || {
            log_error "이미지 다운로드 실패: $image"
            continue
        }
        
        log_info "저장 중: $tar_file"
        docker save "$image" -o "$tar_file"
        
        local size=$(du -h "$tar_file" | cut -f1)
        log_success "저장 완료: $image_name.tar ($size)"
    done
    
    log_success "Docker 이미지 저장 완료"
}

# LLM 모델 다운로드
download_models() {
    if $SKIP_MODELS; then
        log_warn "모델 다운로드 건너뛰기"
        return
    fi
    
    local model_name=$(get_model_name)
    local model_dir="$OUTPUT_DIR/models/$(basename "$model_name")"
    
    log_info "LLM 모델 다운로드 중: $model_name"
    log_info "이 작업은 시간이 오래 걸릴 수 있습니다..."
    
    if [[ -d "$model_dir" ]] && [[ -f "$model_dir/config.json" ]]; then
        log_warn "모델이 이미 존재합니다: $model_dir"
        return
    fi
    
    huggingface-cli download "$model_name" \
        --local-dir "$model_dir" \
        --local-dir-use-symlinks False || {
        log_error "모델 다운로드 실패: $model_name"
        exit 1
    }
    
    local size=$(du -sh "$model_dir" | cut -f1)
    log_success "모델 다운로드 완료: $model_name ($size)"
}

# 프로젝트 소스 복사
copy_source() {
    log_info "프로젝트 소스 복사 중..."
    
    # 필수 파일 복사
    cp -r "$PROJECT_ROOT/apps" "$OUTPUT_DIR/source/"
    cp -r "$PROJECT_ROOT/docker" "$OUTPUT_DIR/source/"
    cp "$PROJECT_ROOT/docker-compose.yml" "$OUTPUT_DIR/source/"
    cp "$PROJECT_ROOT/docker-compose.vllm.yml" "$OUTPUT_DIR/source/" 2>/dev/null || true
    cp "$PROJECT_ROOT/docker-compose.webide.yml" "$OUTPUT_DIR/source/" 2>/dev/null || true
    cp "$PROJECT_ROOT/.env.example" "$OUTPUT_DIR/source/" 2>/dev/null || true
    cp "$PROJECT_ROOT/Makefile" "$OUTPUT_DIR/source/" 2>/dev/null || true
    
    # 문서 복사
    cp -r "$PROJECT_ROOT/docs" "$OUTPUT_DIR/source/"
    
    log_success "프로젝트 소스 복사 완료"
}

# 오프라인 환경용 .env 생성
create_offline_env() {
    log_info "오프라인 환경용 .env 템플릿 생성 중..."
    
    local model_name=$(get_model_name)
    local model_path="/models/$(basename "$model_name")"
    
    cat > "$OUTPUT_DIR/source/.env.offline" << EOF
# ============================================================
# 오프라인 환경 설정 파일
# 생성일: $(date +%Y-%m-%d)
# ============================================================

# 데이터베이스
POSTGRES_USER=cursor
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=cursor_db
DATABASE_URL=postgresql+asyncpg://cursor:CHANGE_ME_STRONG_PASSWORD@db:5432/cursor_db

# Redis
REDIS_URL=redis://redis:6379/0

# 인증 (반드시 변경!)
JWT_SECRET_KEY=CHANGE_ME_32_CHAR_RANDOM_STRING
MASTER_ENCRYPTION_KEY=CHANGE_ME_32_CHAR_ENCRYPTION_KEY

# vLLM (오프라인 모델)
VLLM_BASE_URL=http://vllm:8000/v1
VLLM_MODEL=$model_path
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1

# CORS (내부 네트워크만)
CORS_ALLOWED_ORIGINS=http://localhost:3000

# 프로덕션 설정
DEBUG=false
NODE_ENV=production

# LiteLLM (인증 비활성화 - PoC)
LITELLM_DISABLE_AUTH=true
EOF

    log_success ".env.offline 생성 완료"
}

# 체크섬 생성
generate_checksums() {
    log_info "체크섬 생성 중..."
    
    cd "$OUTPUT_DIR"
    
    find . -type f \( -name "*.tar" -o -name "*.tar.gz" \) \
        -exec sha256sum {} \; > checksums.txt
    
    log_success "체크섬 생성 완료: checksums.txt"
}

# 최종 패키지 압축
create_final_package() {
    log_info "최종 패키지 압축 중..."
    log_warn "이 작업은 시간이 오래 걸릴 수 있습니다..."
    
    local timestamp=$(date +%Y%m%d)
    local package_name="cursor-onprem-offline-${timestamp}.tar.gz"
    local parent_dir=$(dirname "$OUTPUT_DIR")
    
    cd "$parent_dir"
    tar -czvf "$package_name" "$(basename "$OUTPUT_DIR")"
    
    local size=$(du -h "$package_name" | cut -f1)
    log_success "패키지 생성 완료: $package_name ($size)"
    
    echo ""
    log_info "============================================"
    log_info "오프라인 배포 패키지 준비 완료!"
    log_info "============================================"
    log_info "패키지 위치: $parent_dir/$package_name"
    log_info "크기: $size"
    echo ""
    log_info "다음 단계:"
    log_info "1. 패키지를 USB/하드디스크로 복사"
    log_info "2. 오프라인 서버에서 압축 해제"
    log_info "3. docs/offline-deployment.md 참조하여 배포"
    echo ""
}

# 메인 함수
main() {
    echo ""
    echo "============================================"
    echo "  Cursor On-Prem 오프라인 배포 패키지 생성"
    echo "============================================"
    echo ""
    
    parse_args "$@"
    
    log_info "설정:"
    log_info "  - 모델 크기: $MODEL_SIZE ($(get_model_name))"
    log_info "  - 출력 디렉토리: $OUTPUT_DIR"
    log_info "  - 이미지 건너뛰기: $SKIP_IMAGES"
    log_info "  - 모델 건너뛰기: $SKIP_MODELS"
    echo ""
    
    check_requirements
    create_directories
    save_docker_images
    download_models
    copy_source
    create_offline_env
    generate_checksums
    
    # 최종 압축은 선택적
    read -p "최종 패키지로 압축하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_final_package
    else
        log_info "패키지가 준비되었습니다: $OUTPUT_DIR"
    fi
}

# 스크립트 실행
main "$@"
