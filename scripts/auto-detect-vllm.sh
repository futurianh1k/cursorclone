#!/bin/bash
# docker compose up 실행 전 자동으로 GPU/CPU 감지 및 설정
# docker-compose.yml의 depends_on에서 호출되거나 수동 실행 가능

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# GPU 감지 함수 (setup-dev-vllm.sh와 동일)
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

# GPU 메모리에 따른 모델 추천
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

# .env 파일에 설정 추가/업데이트 (조용히)
update_env_quiet() {
    local mode=$1
    local model=$2
    local gpu_memory=$3
    local max_len=$4
    
    # .env 파일이 없으면 생성
    [ ! -f "$ENV_FILE" ] && touch "$ENV_FILE"
    
    # VLLM_MODE
    if grep -q "^VLLM_MODE=" "$ENV_FILE"; then
        sed -i "s|^VLLM_MODE=.*|VLLM_MODE=$mode|" "$ENV_FILE"
    else
        echo "VLLM_MODE=$mode" >> "$ENV_FILE"
    fi
    
    # VLLM_MODEL
    if grep -q "^VLLM_MODEL=" "$ENV_FILE"; then
        sed -i "s|^VLLM_MODEL=.*|VLLM_MODEL=$model|" "$ENV_FILE"
    else
        echo "VLLM_MODEL=$model" >> "$ENV_FILE"
    fi
    
    # VLLM_GPU_MEMORY (GPU 모드일 때만)
    if [ "$mode" = "gpu" ]; then
        if grep -q "^VLLM_GPU_MEMORY=" "$ENV_FILE"; then
            sed -i "s|^VLLM_GPU_MEMORY=.*|VLLM_GPU_MEMORY=$gpu_memory|" "$ENV_FILE"
        else
            echo "VLLM_GPU_MEMORY=$gpu_memory" >> "$ENV_FILE"
        fi
    else
        sed -i '/^VLLM_GPU_MEMORY=/d' "$ENV_FILE"
    fi
    
    # VLLM_MAX_MODEL_LEN
    if grep -q "^VLLM_MAX_MODEL_LEN=" "$ENV_FILE"; then
        sed -i "s|^VLLM_MAX_MODEL_LEN=.*|VLLM_MAX_MODEL_LEN=$max_len|" "$ENV_FILE"
    else
        echo "VLLM_MAX_MODEL_LEN=$max_len" >> "$ENV_FILE"
    fi
}

# 메인 로직
main() {
    cd "$PROJECT_ROOT"
    
    # 이미 설정이 있으면 스킵 (사용자가 수동 설정한 경우)
    if [ -f "$ENV_FILE" ] && grep -q "^VLLM_MODE=" "$ENV_FILE" 2>/dev/null; then
        # 설정이 있으면 그대로 사용
        return 0
    fi
    
    # GPU 감지
    gpu_memory_gb=$(detect_gpu)
    
    if [ -n "$gpu_memory_gb" ]; then
        # GPU 모드
        mode="gpu"
        model=$(recommend_gpu_model "$gpu_memory_gb")
        if [ "$gpu_memory_gb" -lt 8 ]; then
            gpu_memory="0.7"
        elif [ "$gpu_memory_gb" -lt 16 ]; then
            gpu_memory="0.85"
        else
            gpu_memory="0.9"
        fi
        
        case "$model" in
            *1.5B*) max_len="4096" ;;
            *7B*) max_len="8192" ;;
            *14B*) max_len="8192" ;;
            *) max_len="8192" ;;
        esac
    else
        # CPU 모드
        mode="cpu"
        model="Qwen/Qwen2.5-Coder-1.5B-Instruct"
        gpu_memory=""
        max_len="2048"
    fi
    
    # .env 파일 업데이트
    update_env_quiet "$mode" "$model" "$gpu_memory" "$max_len"
}

main "$@"

