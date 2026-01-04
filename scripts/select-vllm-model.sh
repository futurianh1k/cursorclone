#!/bin/bash
# GPU 메모리에 따라 vLLM 모델을 자동 선택하는 스크립트
# 
# 참고: 개발 환경 자동 설정은 setup-dev-vllm.sh를 사용하세요.
#
# 사용법:
#   ./scripts/select-vllm-model.sh
#   ./scripts/select-vllm-model.sh --gpu-memory 8GB
#   ./scripts/select-vllm-model.sh --model Qwen/Qwen2.5-Coder-7B-Instruct

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

# GPU 메모리 확인
get_gpu_memory() {
    if command -v nvidia-smi &> /dev/null; then
        local gpu_memory=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        echo "$gpu_memory"
    else
        echo ""
    fi
}

# GPU 메모리(GB)에 따른 모델 추천
recommend_model() {
    local gpu_memory_gb=$1
    
    if [ -z "$gpu_memory_gb" ]; then
        echo "Qwen/Qwen2.5-Coder-7B-Instruct"  # 기본값
        return
    fi
    
    if [ "$gpu_memory_gb" -lt 4 ]; then
        echo "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    elif [ "$gpu_memory_gb" -lt 8 ]; then
        echo "Qwen/Qwen2.5-Coder-7B-Instruct"
    elif [ "$gpu_memory_gb" -lt 16 ]; then
        echo "Qwen/Qwen2.5-Coder-7B-Instruct"
    elif [ "$gpu_memory_gb" -lt 24 ]; then
        echo "Qwen/Qwen2.5-Coder-14B-Instruct"
    else
        echo "Qwen/Qwen2.5-Coder-32B-Instruct"
    fi
}

# GPU 메모리에 따른 GPU 메모리 사용률 추천
recommend_gpu_memory() {
    local gpu_memory_gb=$1
    
    if [ -z "$gpu_memory_gb" ]; then
        echo "0.9"  # 기본값
        return
    fi
    
    if [ "$gpu_memory_gb" -lt 8 ]; then
        echo "0.7"  # 작은 GPU는 여유를 둠
    elif [ "$gpu_memory_gb" -lt 16 ]; then
        echo "0.85"
    else
        echo "0.9"
    fi
}

# 모델별 최대 컨텍스트 길이 추천
recommend_max_len() {
    local model=$1
    local gpu_memory_gb=$2
    
    case "$model" in
        *1.5B*)
            echo "4096"
            ;;
        *7B*)
            if [ -n "$gpu_memory_gb" ] && [ "$gpu_memory_gb" -lt 8 ]; then
                echo "4096"
            else
                echo "8192"
            fi
            ;;
        *14B*)
            if [ -n "$gpu_memory_gb" ] && [ "$gpu_memory_gb" -lt 16 ]; then
                echo "4096"
            else
                echo "8192"
            fi
            ;;
        *32B*)
            echo "8192"
            ;;
        *)
            echo "8192"
            ;;
    esac
}

# .env 파일 업데이트
update_env_file() {
    local model=$1
    local gpu_memory=$2
    local max_len=$3
    
    log_info ".env 파일 업데이트 중..."
    
    # .env 파일이 없으면 생성
    if [ ! -f "$ENV_FILE" ]; then
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
    fi
    
    # 기존 설정 업데이트 또는 추가
    if grep -q "^VLLM_MODEL=" "$ENV_FILE"; then
        sed -i "s|^VLLM_MODEL=.*|VLLM_MODEL=$model|" "$ENV_FILE"
    else
        echo "VLLM_MODEL=$model" >> "$ENV_FILE"
    fi
    
    if grep -q "^VLLM_GPU_MEMORY=" "$ENV_FILE"; then
        sed -i "s|^VLLM_GPU_MEMORY=.*|VLLM_GPU_MEMORY=$gpu_memory|" "$ENV_FILE"
    else
        echo "VLLM_GPU_MEMORY=$gpu_memory" >> "$ENV_FILE"
    fi
    
    if grep -q "^VLLM_MAX_MODEL_LEN=" "$ENV_FILE"; then
        sed -i "s|^VLLM_MAX_MODEL_LEN=.*|VLLM_MAX_MODEL_LEN=$max_len|" "$ENV_FILE"
    else
        echo "VLLM_MAX_MODEL_LEN=$max_len" >> "$ENV_FILE"
    fi
    
    log_success ".env 파일 업데이트 완료"
}

# 메인 함수
main() {
    local selected_model=""
    local gpu_memory_gb=""
    local manual_gpu_memory=""
    
    # 인자 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            --model)
                selected_model="$2"
                shift 2
                ;;
            --gpu-memory)
                manual_gpu_memory="$2"
                # "8GB" 형식에서 숫자만 추출
                gpu_memory_gb=$(echo "$manual_gpu_memory" | sed 's/[^0-9]//g')
                shift 2
                ;;
            --help|-h)
                echo "사용법: $0 [옵션]"
                echo ""
                echo "옵션:"
                echo "  --model MODEL_NAME          모델 직접 지정"
                echo "  --gpu-memory SIZE           GPU 메모리 크기 (예: 8GB)"
                echo "  --help, -h                  도움말 표시"
                echo ""
                echo "예시:"
                echo "  $0                                    # GPU 자동 감지"
                echo "  $0 --gpu-memory 8GB                  # GPU 메모리 지정"
                echo "  $0 --model Qwen/Qwen2.5-Coder-7B-Instruct"
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                exit 1
                ;;
        esac
    done
    
    echo "=========================================="
    echo "vLLM 모델 선택 도구"
    echo "=========================================="
    echo ""
    
    # GPU 메모리 확인
    if [ -z "$gpu_memory_gb" ]; then
        log_info "GPU 메모리 확인 중..."
        local gpu_memory_mb=$(get_gpu_memory)
        if [ -n "$gpu_memory_mb" ]; then
            gpu_memory_gb=$((gpu_memory_mb / 1024))
            log_success "GPU 메모리: ${gpu_memory_gb}GB"
        else
            log_warn "GPU 메모리를 자동으로 감지할 수 없습니다."
            log_info "기본 모델을 사용합니다: Qwen/Qwen2.5-Coder-7B-Instruct"
        fi
    else
        log_info "GPU 메모리: ${gpu_memory_gb}GB (수동 지정)"
    fi
    
    echo ""
    
    # 모델 선택
    if [ -z "$selected_model" ]; then
        selected_model=$(recommend_model "$gpu_memory_gb")
        log_info "추천 모델: $selected_model"
    else
        log_info "지정된 모델: $selected_model"
    fi
    
    # GPU 메모리 사용률 추천
    local recommended_gpu_memory=$(recommend_gpu_memory "$gpu_memory_gb")
    log_info "GPU 메모리 사용률: ${recommended_gpu_memory}"
    
    # 최대 컨텍스트 길이 추천
    local recommended_max_len=$(recommend_max_len "$selected_model" "$gpu_memory_gb")
    log_info "최대 컨텍스트 길이: ${recommended_max_len}"
    
    echo ""
    echo "=========================================="
    echo "모델별 GPU 메모리 요구사항"
    echo "=========================================="
    echo "Qwen/Qwen2.5-Coder-1.5B-Instruct  →  4GB 이상"
    echo "Qwen/Qwen2.5-Coder-7B-Instruct   →  8GB 이상 (기본값)"
    echo "Qwen/Qwen2.5-Coder-14B-Instruct  →  16GB 이상"
    echo "Qwen/Qwen2.5-Coder-32B-Instruct  →  24GB 이상"
    echo ""
    
    # 확인
    read -p "이 설정으로 진행하시겠습니까? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log_info "취소되었습니다."
        exit 0
    fi
    
    # .env 파일 업데이트
    update_env_file "$selected_model" "$recommended_gpu_memory" "$recommended_max_len"
    
    echo ""
    log_success "설정 완료!"
    echo ""
    echo "다음 명령으로 vLLM 서버를 시작하세요:"
    echo "  docker compose --profile gpu up -d vllm"
    echo ""
    echo "현재 설정:"
    echo "  모델: $selected_model"
    echo "  GPU 메모리 사용률: $recommended_gpu_memory"
    echo "  최대 컨텍스트 길이: $recommended_max_len"
}

main "$@"

