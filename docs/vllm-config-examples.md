# vLLM 모델 설정 예시

GPU 메모리에 따라 vLLM 모델을 선택하는 설정 예시입니다.

## 📋 설정 파일 위치

주요 설정 파일:
- `docker-compose.yml` - 기본 vLLM 설정
- `docker-compose.vllm.yml` - 추가 vLLM 설정 (권장)
- `.env` - 환경변수 설정 (프로젝트 루트)

## 🎯 GPU 메모리별 설정 예시

### 예시 1: 4GB GPU (RTX 3050, GTX 1650 등)

```bash
# .env 파일 또는 환경변수
export VLLM_MODEL=Qwen/Qwen2.5-Coder-1.5B-Instruct
export VLLM_GPU_MEMORY=0.7
export VLLM_MAX_MODEL_LEN=4096
```

**docker-compose.yml 사용 시:**
```yaml
vllm:
  environment:
    VLLM_MODEL: Qwen/Qwen2.5-Coder-1.5B-Instruct
    VLLM_GPU_MEMORY: 0.7
    VLLM_MAX_MODEL_LEN: 4096
```

### 예시 2: 8GB GPU (RTX 3060 Ti, RTX 3070 등) - 기본값

```bash
# .env 파일 또는 환경변수
export VLLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
export VLLM_GPU_MEMORY=0.9
export VLLM_MAX_MODEL_LEN=8192
```

**docker-compose.yml 사용 시:**
```yaml
vllm:
  environment:
    VLLM_MODEL: Qwen/Qwen2.5-Coder-7B-Instruct
    VLLM_GPU_MEMORY: 0.9
    VLLM_MAX_MODEL_LEN: 8192
```

### 예시 3: 16GB GPU (RTX 4080, A4000 등)

```bash
# .env 파일 또는 환경변수
export VLLM_MODEL=Qwen/Qwen2.5-Coder-14B-Instruct
export VLLM_GPU_MEMORY=0.9
export VLLM_MAX_MODEL_LEN=8192
```

**docker-compose.yml 사용 시:**
```yaml
vllm:
  environment:
    VLLM_MODEL: Qwen/Qwen2.5-Coder-14B-Instruct
    VLLM_GPU_MEMORY: 0.9
    VLLM_MAX_MODEL_LEN: 8192
```

### 예시 4: 24GB+ GPU (RTX 4090, A100 등)

```bash
# .env 파일 또는 환경변수
export VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
export VLLM_GPU_MEMORY=0.9
export VLLM_MAX_MODEL_LEN=16384
```

**docker-compose.yml 사용 시:**
```yaml
vllm:
  environment:
    VLLM_MODEL: Qwen/Qwen2.5-Coder-32B-Instruct
    VLLM_GPU_MEMORY: 0.9
    VLLM_MAX_MODEL_LEN: 16384
```

## 🔧 설정 방법

### 방법 1: 환경변수로 설정 (권장)

```bash
# 프로젝트 루트에서
cd /home/ubuntu/projects/cursorclone

# .env 파일 생성/수정
cat >> .env << EOF
VLLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
VLLM_GPU_MEMORY=0.9
VLLM_MAX_MODEL_LEN=8192
EOF

# vLLM 서버 시작
docker compose --profile gpu up -d vllm
```

### 방법 2: docker-compose.yml 직접 수정

```yaml
# docker-compose.yml의 vllm 서비스 섹션
vllm:
  environment:
    VLLM_MODEL: Qwen/Qwen2.5-Coder-7B-Instruct  # 원하는 모델로 변경
    VLLM_GPU_MEMORY: 0.9                         # 0.7 ~ 0.95
    VLLM_MAX_MODEL_LEN: 8192                     # 4096, 8192, 16384
```

### 방법 3: 자동 선택 스크립트 사용

```bash
# GPU 메모리 자동 감지 및 모델 선택
./scripts/select-vllm-model.sh

# GPU 메모리 수동 지정
./scripts/select-vllm-model.sh --gpu-memory 8GB

# 모델 직접 지정
./scripts/select-vllm-model.sh --model Qwen/Qwen2.5-Coder-7B-Instruct
```

## 📊 현재 설정 확인

```bash
# 환경변수 확인
docker compose config | grep -A 10 "vllm:"

# 실행 중인 컨테이너의 환경변수 확인
docker compose exec vllm printenv | grep VLLM

# vLLM 서버 로그에서 모델 확인
docker compose logs vllm | grep -i "model\|loading"
```

## ⚙️ docker-compose.yml 설정 코드

현재 `docker-compose.yml`의 vLLM 설정:

```yaml
vllm:
  image: vllm/vllm-openai:latest
  container_name: cursor-poc-vllm
  environment:
    VLLM_API_KEY: ${VLLM_API_KEY:-}
    VLLM_MODEL: ${VLLM_MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}
    VLLM_GPU_MEMORY: ${VLLM_GPU_MEMORY:-0.9}
    VLLM_MAX_MODEL_LEN: ${VLLM_MAX_MODEL_LEN:-8192}
  command:
    - "${VLLM_MODEL:-Qwen/Qwen2.5-Coder-7B-Instruct}"
    - "--host"
    - "0.0.0.0"
    - "--port"
    - "8000"
    - "--trust-remote-code"
    - "--max-model-len"
    - "${VLLM_MAX_MODEL_LEN:-8192}"
    - "--gpu-memory-utilization"
    - "${VLLM_GPU_MEMORY:-0.9}"
```

## 🚀 사용 예시

### RTX 3060 Ti (8GB) 사용 시

```bash
# 1. 환경변수 설정
export VLLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
export VLLM_GPU_MEMORY=0.85
export VLLM_MAX_MODEL_LEN=8192

# 2. vLLM 서버 시작
docker compose --profile gpu up -d vllm

# 3. 상태 확인
docker compose ps vllm
docker compose logs vllm --tail 50
```

### 더 작은 GPU (4GB) 사용 시

```bash
# 1. 작은 모델 선택
export VLLM_MODEL=Qwen/Qwen2.5-Coder-1.5B-Instruct
export VLLM_GPU_MEMORY=0.7
export VLLM_MAX_MODEL_LEN=4096

# 2. vLLM 서버 시작
docker compose --profile gpu up -d vllm
```

## 📝 참고사항

1. **환경변수 우선순위**: `.env` 파일 > `docker-compose.yml` > 기본값
2. **모델 변경 후**: 컨테이너 재시작 필요
3. **GPU 메모리 확인**: `nvidia-smi` 명령으로 확인
4. **OOM 에러 시**: 더 작은 모델 또는 낮은 GPU 메모리 사용률 사용

## 🔗 관련 문서

- [모델 선택 가이드](./vllm-model-selection.md)
- [GPU 설정 가이드](./vllm-gpu-setup.md)

