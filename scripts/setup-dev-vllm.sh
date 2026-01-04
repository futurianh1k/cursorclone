#!/bin/bash
# 개발 환경용 vLLM 자동 설정 스크립트
# GPU/CPU 자동 감지 및 적절한 모델/설정 선택
#
# 사용법:
#   ./scripts/setup-dev-vllm.sh
#   ./scripts/setup-dev-vllm.sh --force-cpu
#   ./scripts/setup-dev-vllm.sh --force-gpu

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# 색상 출력
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# GPU 감지
detect_gpu() {
    if command -v nvidia-smi &> /dev/null; then
        if nvidia-smi &> /dev/null; then
            local gpu_memory_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
            if [ -n "$gpu_memory_mb" ] && [ "$gpu_memory_mb" -gt 0 ]; then
                local gpu_memory_gb=$((gpu_memory_mb / 1024))
                echo "$gpu_memory_gb"
                return 0
            fi
        fi
    fi
    echo ""
    return 1
}

# GPU 메모리에 따른 모델 추천 (GPU 모드)
recommend_gpu_model() {
    local gpu_memory_gb=$1
    
    if [ -z "$gpu_memory_gb" ] || [ "$gpu_memory_gb" -lt 4 ]; then
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
    
    if [ -z "$gpu_memory_gb" ] || [ "$gpu_memory_gb" -lt 8 ]; then
        echo "0.7"
    elif [ "$gpu_memory_gb" -lt 16 ]; then
        echo "0.85"
    else
        echo "0.9"
    fi
}

# GPU 메모리에 따른 최대 컨텍스트 길이 추천
recommend_max_len_gpu() {
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

# CPU 모드용 모델 추천 (가장 작은 모델)
recommend_cpu_model() {
    echo "Qwen/Qwen2.5-Coder-1.5B-Instruct"
}

# CPU 모드용 최대 컨텍스트 길이 (메모리 절약)
recommend_max_len_cpu() {
    echo "2048"  # CPU 모드는 메모리 제약이 크므로 짧게
}

# .env 파일 업데이트
update_env_file() {
    local mode=$1  # "gpu" or "cpu"
    local model=$2
    local gpu_memory=$3
    local max_len=$4
    
    log_info ".env 파일 업데이트 중..."
    
    # .env 파일이 없으면 생성
    if [ ! -f "$ENV_FILE" ]; then
        touch "$ENV_FILE"
    fi
    
    # 모드 설정
    if grep -q "^VLLM_MODE=" "$ENV_FILE"; then
        sed -i "s|^VLLM_MODE=.*|VLLM_MODE=$mode|" "$ENV_FILE"
    else
        echo "VLLM_MODE=$mode" >> "$ENV_FILE"
    fi
    
    # 모델 설정
    if grep -q "^VLLM_MODEL=" "$ENV_FILE"; then
        sed -i "s|^VLLM_MODEL=.*|VLLM_MODEL=$model|" "$ENV_FILE"
    else
        echo "VLLM_MODEL=$model" >> "$ENV_FILE"
    fi
    
    # GPU 메모리 사용률 (GPU 모드일 때만)
    if [ "$mode" = "gpu" ]; then
        if grep -q "^VLLM_GPU_MEMORY=" "$ENV_FILE"; then
            sed -i "s|^VLLM_GPU_MEMORY=.*|VLLM_GPU_MEMORY=$gpu_memory|" "$ENV_FILE"
        else
            echo "VLLM_GPU_MEMORY=$gpu_memory" >> "$ENV_FILE"
        fi
    else
        # CPU 모드에서는 GPU 메모리 설정 제거
        sed -i '/^VLLM_GPU_MEMORY=/d' "$ENV_FILE"
    fi
    
    # 최대 컨텍스트 길이
    if grep -q "^VLLM_MAX_MODEL_LEN=" "$ENV_FILE"; then
        sed -i "s|^VLLM_MAX_MODEL_LEN=.*|VLLM_MAX_MODEL_LEN=$max_len|" "$ENV_FILE"
    else
        echo "VLLM_MAX_MODEL_LEN=$max_len" >> "$ENV_FILE"
    fi
    
    log_success ".env 파일 업데이트 완료"
}

# Docker Compose 파일 선택
select_compose_file() {
    local mode=$1
    
    if [ "$mode" = "cpu" ]; then
        echo "docker-compose.vllm-cpu.yml"
    else
        echo "docker-compose.vllm.yml"
    fi
}

# 메인 함수
main() {
    local force_mode=""  # "cpu" or "gpu" or ""
    local gpu_memory_gb=""
    local mode=""
    
    # 인자 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force-cpu)
                force_mode="cpu"
                shift
                ;;
            --force-gpu)
                force_mode="gpu"
                shift
                ;;
            --help|-h)
                echo "사용법: $0 [옵션]"
                echo ""
                echo "옵션:"
                echo "  --force-cpu          CPU 모드 강제 사용 (GPU 무시)"
                echo "  --force-gpu          GPU 모드 강제 사용"
                echo "  --help, -h           도움말 표시"
                echo ""
                echo "예시:"
                echo "  $0                          # GPU/CPU 자동 감지"
                echo "  $0 --force-cpu              # CPU 모드 강제"
                echo "  $0 --force-gpu              # GPU 모드 강제"
                exit 0
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                exit 1
                ;;
        esac
    done
    
    log_section "개발 환경 vLLM 자동 설정"
    
    # GPU 감지
    log_info "하드웨어 감지 중..."
    
    if [ "$force_mode" = "cpu" ]; then
        mode="cpu"
        log_warn "CPU 모드 강제 사용 (--force-cpu)"
    elif [ "$force_mode" = "gpu" ]; then
        mode="gpu"
        log_warn "GPU 모드 강제 사용 (--force-gpu)"
        gpu_memory_gb=$(detect_gpu)
        if [ -z "$gpu_memory_gb" ]; then
            log_error "GPU를 찾을 수 없습니다. --force-gpu 옵션을 제거하거나 GPU를 확인하세요."
            exit 1
        fi
    else
        # 자동 감지
        gpu_memory_gb=$(detect_gpu)
        if [ -n "$gpu_memory_gb" ]; then
            mode="gpu"
            log_success "GPU 감지됨: ${gpu_memory_gb}GB"
        else
            mode="cpu"
            log_warn "GPU를 찾을 수 없습니다. CPU 모드로 전환합니다."
        fi
    fi
    
    echo ""
    
    # 모델 및 설정 선택
    local selected_model=""
    local gpu_memory_util=""
    local max_len=""
    
    if [ "$mode" = "gpu" ]; then
        log_section "GPU 모드 설정"
        selected_model=$(recommend_gpu_model "$gpu_memory_gb")
        gpu_memory_util=$(recommend_gpu_memory "$gpu_memory_gb")
        max_len=$(recommend_max_len_gpu "$selected_model" "$gpu_memory_gb")
        
        log_info "모델: $selected_model"
        log_info "GPU 메모리: ${gpu_memory_gb}GB"
        log_info "GPU 메모리 사용률: ${gpu_memory_util}"
        log_info "최대 컨텍스트 길이: ${max_len}"
    else
        log_section "CPU 모드 설정"
        selected_model=$(recommend_cpu_model)
        max_len=$(recommend_max_len_cpu)
        
        log_info "모델: $selected_model (CPU 최적화)"
        log_info "최대 컨텍스트 길이: ${max_len} (메모리 절약)"
        log_warn "CPU 모드는 매우 느립니다. 개발/테스트 목적으로만 사용하세요."
    fi
    
    echo ""
    log_section "모델별 요구사항"
    
    if [ "$mode" = "gpu" ]; then
        echo -e "GPU 모드:"
        echo -e "  Qwen/Qwen2.5-Coder-1.5B-Instruct  →  4GB 이상"
        echo -e "  Qwen/Qwen2.5-Coder-7B-Instruct   →  8GB 이상"
        echo -e "  Qwen/Qwen2.5-Coder-14B-Instruct  →  16GB 이상"
        echo -e "  Qwen/Qwen2.5-Coder-32B-Instruct  →  24GB 이상"
    else
        echo -e "CPU 모드:"
        echo -e "  Qwen/Qwen2.5-Coder-1.5B-Instruct  →  RAM 8GB+ 권장"
        echo -e "  ⚠️  CPU 모드는 매우 느리며 프로덕션 사용 비권장"
    fi
    
    echo ""
    
    # 모델 선택
    log_section "모델 선택"
    echo -e "추천 모델: ${CYAN}$selected_model${NC}"
    echo ""
    echo -e "다음 중 선택하세요:"
    echo -e "  ${GREEN}y${NC}  - 추천 모델 사용 ($selected_model)"
    echo -e "  ${GREEN}n${NC}  - 다른 모델 선택"
    echo -e "  ${GREEN}c${NC}  - 취소"
    echo ""
    read -p "선택 (y/n/c): " model_choice
    
    case "$model_choice" in
        [Yy])
            # 추천 모델 사용 (이미 selected_model에 설정됨)
            log_info "추천 모델을 사용합니다: $selected_model"
            ;;
        [Nn])
            # 다른 모델 선택
            echo ""
            echo -e "사용 가능한 모델:"
            echo ""
            if [ "$mode" = "gpu" ]; then
                echo -e "  1) Qwen/Qwen2.5-Coder-1.5B-Instruct  (4GB+ GPU)"
                echo -e "  2) Qwen/Qwen2.5-Coder-7B-Instruct   (8GB+ GPU)"
                echo -e "  3) Qwen/Qwen2.5-Coder-14B-Instruct  (16GB+ GPU)"
                echo -e "  4) Qwen/Qwen2.5-Coder-32B-Instruct  (24GB+ GPU)"
            else
                echo -e "  1) Qwen/Qwen2.5-Coder-1.5B-Instruct  (CPU 최적화)"
            fi
            echo -e "  5) 직접 입력 (HuggingFace 모델 이름)"
            echo ""
            read -p "모델 선택 (1-5): " model_num
            
            case "$model_num" in
                1)
                    selected_model="Qwen/Qwen2.5-Coder-1.5B-Instruct"
                    ;;
                2)
                    if [ "$mode" = "gpu" ]; then
                        selected_model="Qwen/Qwen2.5-Coder-7B-Instruct"
                    else
                        log_error "CPU 모드에서는 1.5B 모델만 지원됩니다."
                        exit 1
                    fi
                    ;;
                3)
                    if [ "$mode" = "gpu" ]; then
                        selected_model="Qwen/Qwen2.5-Coder-14B-Instruct"
                    else
                        log_error "CPU 모드에서는 1.5B 모델만 지원됩니다."
                        exit 1
                    fi
                    ;;
                4)
                    if [ "$mode" = "gpu" ]; then
                        selected_model="Qwen/Qwen2.5-Coder-32B-Instruct"
                    else
                        log_error "CPU 모드에서는 1.5B 모델만 지원됩니다."
                        exit 1
                    fi
                    ;;
                5)
                    echo ""
                    read -p "모델 이름을 입력하세요 (예: Qwen/Qwen2.5-Coder-7B-Instruct): " custom_model
                    if [ -z "$custom_model" ]; then
                        log_error "모델 이름이 입력되지 않았습니다."
                        exit 1
                    fi
                    selected_model="$custom_model"
                    log_warn "사용자 지정 모델: $selected_model"
                    log_warn "이 모델이 시스템 사양에 맞는지 확인하세요."
                    ;;
                *)
                    log_error "잘못된 선택입니다."
                    exit 1
                    ;;
            esac
            
            # 선택한 모델에 맞게 설정 재계산
            if [ "$mode" = "gpu" ]; then
                if [ "$model_num" = "5" ]; then
                    # 사용자 지정 모델의 경우 모델 이름에서 크기 추정
                    log_info "사용자 지정 모델의 경우 모델 크기에 따라 설정을 추정합니다."
                    if [[ "$selected_model" =~ 1\.5[Bb]|1\.8[Bb] ]]; then
                        max_len="4096"
                    elif [[ "$selected_model" =~ 7[Bb] ]]; then
                        max_len="8192"
                    elif [[ "$selected_model" =~ 14[Bb]|13[Bb] ]]; then
                        max_len="8192"
                    elif [[ "$selected_model" =~ 32[Bb]|30[Bb]|34[Bb] ]]; then
                        max_len="8192"
                    else
                        max_len="8192"  # 기본값
                    fi
                else
                    max_len=$(recommend_max_len_gpu "$selected_model" "$gpu_memory_gb")
                fi
            else
                max_len=$(recommend_max_len_cpu)
            fi
            
            log_success "선택한 모델: $selected_model"
            ;;
        [Cc]|"")
            log_info "취소되었습니다."
            exit 0
            ;;
        *)
            log_error "잘못된 선택입니다."
            exit 1
            ;;
    esac
    
    echo ""
    
    # GPU 메모리 사용률 설정 (GPU 모드일 때)
    if [ "$mode" = "gpu" ]; then
        log_section "GPU 메모리 사용률 설정"
        echo -e "현재 추천값: ${CYAN}${gpu_memory_util}${NC}"
        echo ""
        read -p "GPU 메모리 사용률을 변경하시겠습니까? (y/N): " change_gpu_mem
        if [[ "$change_gpu_mem" =~ ^[Yy]$ ]]; then
            read -p "GPU 메모리 사용률 (0.1-1.0, 기본값: $gpu_memory_util): " custom_gpu_mem
            if [ -n "$custom_gpu_mem" ]; then
                # 유효성 검사 (bc 없이 bash로 처리)
                if command -v bc &> /dev/null; then
                    # bc가 있으면 사용
                    if (( $(echo "$custom_gpu_mem >= 0.1 && $custom_gpu_mem <= 1.0" | bc -l) )); then
                        gpu_memory_util="$custom_gpu_mem"
                        log_success "GPU 메모리 사용률: $gpu_memory_util"
                    else
                        log_warn "잘못된 값입니다. 추천값을 사용합니다: $gpu_memory_util"
                    fi
                else
                    # bc가 없으면 간단한 검증 (0.1-1.0 범위)
                    if awk "BEGIN {exit !($custom_gpu_mem >= 0.1 && $custom_gpu_mem <= 1.0)}" 2>/dev/null; then
                        gpu_memory_util="$custom_gpu_mem"
                        log_success "GPU 메모리 사용률: $gpu_memory_util"
                    else
                        log_warn "잘못된 값입니다. 추천값을 사용합니다: $gpu_memory_util"
                    fi
                fi
            fi
        fi
        echo ""
    fi
    
    # 최대 컨텍스트 길이 설정
    log_section "최대 컨텍스트 길이 설정"
    echo -e "현재 추천값: ${CYAN}${max_len}${NC}"
    echo ""
    read -p "최대 컨텍스트 길이를 변경하시겠습니까? (y/N): " change_max_len
    if [[ "$change_max_len" =~ ^[Yy]$ ]]; then
        read -p "최대 컨텍스트 길이 (1024-32768, 기본값: $max_len): " custom_max_len
        if [ -n "$custom_max_len" ]; then
            # 유효성 검사
            if [ "$custom_max_len" -ge 1024 ] && [ "$custom_max_len" -le 32768 ] 2>/dev/null; then
                max_len="$custom_max_len"
                log_success "최대 컨텍스트 길이: $max_len"
            else
                log_warn "잘못된 값입니다. 추천값을 사용합니다: $max_len"
            fi
        fi
    fi
    
    echo ""
    log_section "최종 설정 확인"
    echo -e "  모드: $mode"
    echo -e "  모델: $selected_model"
    if [ "$mode" = "gpu" ]; then
        echo -e "  GPU 메모리: ${gpu_memory_gb}GB"
        echo -e "  GPU 메모리 사용률: ${gpu_memory_util}"
    fi
    echo -e "  최대 컨텍스트 길이: ${max_len}"
    echo ""
    
    # 최종 확인
    read -p "이 설정으로 진행하시겠습니까? (y/N): " final_confirm
    if [[ ! "$final_confirm" =~ ^[Yy]$ ]]; then
        log_info "취소되었습니다."
        exit 0
    fi
    
    # .env 파일 업데이트
    update_env_file "$mode" "$selected_model" "$gpu_memory_util" "$max_len"
    
    # Docker Compose 파일 선택
    local compose_file=$(select_compose_file "$mode")
    
    echo ""
    log_success "설정 완료!"
    echo ""
    echo "다음 명령으로 vLLM 서버를 시작하세요:"
    echo ""
    
    if [ "$mode" = "gpu" ]; then
        echo "  docker compose -f docker-compose.yml -f docker-compose.vllm.yml up -d vllm"
    else
        echo "  docker compose -f docker-compose.yml -f docker-compose.vllm-cpu.yml up -d vllm"
    fi
    
    echo ""
    echo -e "현재 설정:"
    echo -e "  모드: $mode"
    echo -e "  모델: $selected_model"
    if [ "$mode" = "gpu" ]; then
        echo -e "  GPU 메모리: ${gpu_memory_gb}GB"
        echo -e "  GPU 메모리 사용률: ${gpu_memory_util}"
    fi
    echo -e "  최대 컨텍스트 길이: ${max_len}"
    echo ""
    echo -e "설정 파일: $ENV_FILE"
    echo -e "Compose 파일: $compose_file"
}

main "$@"

