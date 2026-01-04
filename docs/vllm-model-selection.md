# vLLM 모델 선택 가이드

GPU 메모리에 따라 적절한 vLLM 모델을 선택하는 방법입니다.

## 📊 모델별 GPU 메모리 요구사항

| 모델 | 파라미터 | 최소 GPU 메모리 | 권장 GPU 메모리 | 설명 |
|------|---------|----------------|----------------|------|
| **Qwen/Qwen2.5-Coder-1.5B-Instruct** | 1.5B | 4GB | 6GB | 가장 작은 모델, 빠른 응답 |
| **Qwen/Qwen2.5-Coder-7B-Instruct** | 7B | 8GB | 12GB | **기본값**, 균형잡힌 성능 |
| **Qwen/Qwen2.5-Coder-14B-Instruct** | 14B | 16GB | 20GB | 더 나은 코드 품질 |
| **Qwen/Qwen2.5-Coder-32B-Instruct** | 32B | 24GB | 32GB+ | 최고 품질, 가장 느림 |

## 🚀 빠른 시작

### 방법 1: 자동 선택 스크립트 사용 (권장)

```bash
# GPU 메모리 자동 감지 및 모델 선택
./scripts/select-vllm-model.sh

# GPU 메모리 수동 지정
./scripts/select-vllm-model.sh --gpu-memory 8GB

# 모델 직접 지정
./scripts/select-vllm-model.sh --model Qwen/Qwen2.5-Coder-7B-Instruct
```

### 방법 2: 환경변수로 직접 설정

#### 1. `.env` 파일 생성/수정

```bash
cd /home/ubuntu/projects/cursorclone
cp .env.example .env
```

#### 2. 모델 선택

`.env` 파일에서 다음 변수를 수정:

```bash
# 8GB GPU 예시
VLLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
VLLM_GPU_MEMORY=0.9
VLLM_MAX_MODEL_LEN=8192

# 4GB GPU 예시 (작은 모델 사용)
VLLM_MODEL=Qwen/Qwen2.5-Coder-1.5B-Instruct
VLLM_GPU_MEMORY=0.7
VLLM_MAX_MODEL_LEN=4096

# 16GB GPU 예시 (큰 모델 사용)
VLLM_MODEL=Qwen/Qwen2.5-Coder-14B-Instruct
VLLM_GPU_MEMORY=0.9
VLLM_MAX_MODEL_LEN=8192
```

#### 3. vLLM 서버 시작

```bash
docker compose --profile gpu up -d vllm
```

## ⚙️ 설정 파일 위치

### docker-compose.yml (기본 설정)

```yaml
vllm:
  environment:
    VLLM_MODEL: ${VLLM_MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}
  command:
    - "${VLLM_MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}"
    - "--gpu-memory-utilization"
    - "${VLLM_GPU_MEMORY:-0.9}"
    - "--max-model-len"
    - "${VLLM_MAX_MODEL_LEN:-8192}"
```

### docker-compose.vllm.yml (추가 설정)

```yaml
vllm:
  command: >
    --model ${VLLM_MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}
    --gpu-memory-utilization ${VLLM_GPU_MEMORY:-0.9}
    --max-model-len ${VLLM_MAX_MODEL_LEN:-8192}
```

## 🔧 GPU 메모리 사용률 조정

GPU 메모리가 부족한 경우:

```bash
# 기본값: 0.9 (90%)
VLLM_GPU_MEMORY=0.9

# 여유를 두고 싶은 경우: 0.7 ~ 0.8
VLLM_GPU_MEMORY=0.7

# 최대 활용: 0.95 (주의: OOM 위험)
VLLM_GPU_MEMORY=0.95
```

## 📏 최대 컨텍스트 길이 조정

GPU 메모리가 부족하면 컨텍스트 길이를 줄이세요:

```bash
# 기본값: 8192 토큰
VLLM_MAX_MODEL_LEN=8192

# 메모리 부족 시: 4096 토큰
VLLM_MAX_MODEL_LEN=4096

# 더 긴 컨텍스트 필요 시: 16384 토큰 (큰 모델만)
VLLM_MAX_MODEL_LEN=16384
```

## 🎯 GPU 메모리 확인 방법

```bash
# GPU 메모리 확인
nvidia-smi

# 또는
nvidia-smi --query-gpu=memory.total,memory.free --format=csv
```

## 📝 설정 예시

### 예시 1: RTX 3060 Ti (8GB)

```bash
# .env 파일
VLLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
VLLM_GPU_MEMORY=0.85
VLLM_MAX_MODEL_LEN=8192
```

### 예시 2: RTX 4090 (24GB)

```bash
# .env 파일
VLLM_MODEL=Qwen/Qwen2.5-Coder-14B-Instruct
VLLM_GPU_MEMORY=0.9
VLLM_MAX_MODEL_LEN=16384
```

### 예시 3: 작은 GPU (4GB)

```bash
# .env 파일
VLLM_MODEL=Qwen/Qwen2.5-Coder-1.5B-Instruct
VLLM_GPU_MEMORY=0.7
VLLM_MAX_MODEL_LEN=4096
```

## 🔍 현재 설정 확인

```bash
# 환경변수 확인
docker compose exec api printenv | grep VLLM

# vLLM 서버 로그 확인
docker compose logs vllm --tail 50

# GPU 사용량 확인
docker compose exec vllm nvidia-smi
```

## ⚠️ 문제 해결

### OOM (Out of Memory) 에러 발생 시

1. **더 작은 모델 사용**
   ```bash
   VLLM_MODEL=Qwen/Qwen2.5-Coder-1.5B-Instruct
   ```

2. **GPU 메모리 사용률 낮추기**
   ```bash
   VLLM_GPU_MEMORY=0.7
   ```

3. **컨텍스트 길이 줄이기**
   ```bash
   VLLM_MAX_MODEL_LEN=4096
   ```

### 모델 로딩이 너무 느릴 때

- 더 작은 모델 사용
- GPU 메모리 사용률 높이기 (0.95까지)
- `--dtype half` 옵션 추가 (자동으로 적용됨)

## 📚 참고 자료

- [vLLM 공식 문서](https://docs.vllm.ai/)
- [Qwen 모델 카드](https://huggingface.co/Qwen)
- [GPU 메모리 계산기](https://huggingface.co/docs/transformers/main/en/perf_infer_gpu_one)

