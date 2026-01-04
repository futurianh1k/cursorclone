# 로컬 개발 환경 설정 가이드

개발자들이 각자 로컬 PC에서 vLLM을 구동하는 방법입니다.

## 🎯 개요

- **목적**: 클라우드 비용 절감을 위해 로컬 PC에서 vLLM 구동
- **자동 감지**: GPU/CPU 자동 감지 및 적절한 모델 선택
- **유연성**: GPU가 없어도 CPU 모드로 개발 가능

## 🚀 빠른 시작

### 1단계: 자동 설정 (권장)

```bash
cd /home/ubuntu/projects/cursorclone

# GPU/CPU 자동 감지 및 설정
make -f Makefile.dev dev-vllm-setup

# 또는 직접 스크립트 실행
./scripts/setup-dev-vllm.sh
```

스크립트가 자동으로:
- ✅ GPU/CPU 감지
- ✅ 적절한 모델 추천
- ✅ 사용자에게 모델 선택 옵션 제공
- ✅ `.env` 파일 생성/업데이트

**모델 선택 옵션:**
- `y` - 추천 모델 사용
- `n` - 다른 모델 선택 (메뉴에서 선택하거나 직접 입력)
- `c` - 취소

추가로 GPU 메모리 사용률과 최대 컨텍스트 길이도 수정할 수 있습니다.

### 2단계: vLLM 서버 시작

```bash
# 자동으로 GPU/CPU 모드 선택하여 시작
make -f Makefile.dev dev-vllm-start

# 또는 직접 실행
# GPU 모드:
docker compose --profile gpu -f docker-compose.yml -f docker-compose.vllm.yml up -d vllm

# CPU 모드:
docker compose -f docker-compose.yml -f docker-compose.vllm-cpu.yml up -d vllm
```

### 3단계: 상태 확인

```bash
make -f Makefile.dev dev-vllm-status
```

## 📋 모드별 설정

### GPU 모드 (자동 감지)

GPU가 감지되면 GPU 메모리에 따라 모델이 자동 선택됩니다:

| GPU 메모리 | 선택되는 모델 | GPU 메모리 사용률 | 컨텍스트 길이 |
|-----------|--------------|-----------------|--------------|
| 4GB 이하 | Qwen/Qwen2.5-Coder-1.5B-Instruct | 0.7 | 4096 |
| 8GB | Qwen/Qwen2.5-Coder-7B-Instruct | 0.9 | 8192 |
| 16GB | Qwen/Qwen2.5-Coder-14B-Instruct | 0.9 | 8192 |
| 24GB+ | Qwen/Qwen2.5-Coder-32B-Instruct | 0.9 | 8192 |

### CPU 모드 (GPU 없을 때)

GPU가 없으면 자동으로 CPU 모드로 전환됩니다:

- **모델**: Qwen/Qwen2.5-Coder-1.5B-Instruct (가장 작은 모델)
- **컨텍스트 길이**: 2048 (메모리 절약)
- **주의**: 
  - ⚠️ CPU 모드는 매우 느리며 개발/테스트 목적으로만 사용
  - ⚠️ vLLM의 CPU 모드는 실험적 기능이며, 안정성이 보장되지 않음
  - 💡 CPU 모드가 작동하지 않으면 `DEV_MODE=true`로 Mock 응답 사용 권장

## 🔧 수동 설정

### GPU 모드 강제 사용

```bash
./scripts/setup-dev-vllm.sh --force-gpu
```

### CPU 모드 강제 사용

```bash
./scripts/setup-dev-vllm.sh --force-cpu
```

### 특정 모델 지정

**방법 1: 설정 스크립트에서 선택 (권장)**

```bash
make -f Makefile.dev dev-vllm-setup
# 모델 선택 메뉴에서 원하는 모델 선택
# - 추천 모델 사용 (y)
# - 다른 모델 선택 (n) → 메뉴에서 선택하거나 직접 입력
```

**방법 2: .env 파일 직접 수정**

```bash
# .env 파일 수정
VLLM_MODEL=Qwen/Qwen2.5-Coder-7B-Instruct
VLLM_GPU_MEMORY=0.9
VLLM_MAX_MODEL_LEN=8192
VLLM_MODE=gpu  # 또는 cpu
```

**사용 가능한 모델:**
- `Qwen/Qwen2.5-Coder-1.5B-Instruct` - 4GB+ GPU 또는 CPU
- `Qwen/Qwen2.5-Coder-7B-Instruct` - 8GB+ GPU
- `Qwen/Qwen2.5-Coder-14B-Instruct` - 16GB+ GPU
- `Qwen/Qwen2.5-Coder-32B-Instruct` - 24GB+ GPU
- 기타 HuggingFace 모델 (직접 입력 가능)

## 📝 Makefile 명령어

```bash
# 설정
make -f Makefile.dev dev-vllm-setup       # 자동 감지
make -f Makefile.dev dev-vllm-setup-cpu   # CPU 모드 강제
make -f Makefile.dev dev-vllm-setup-gpu   # GPU 모드 강제

# 실행
make -f Makefile.dev dev-vllm-start       # 시작
make -f Makefile.dev dev-vllm-stop        # 중지
make -f Makefile.dev dev-vllm-restart     # 재시작

# 확인
make -f Makefile.dev dev-vllm-status      # 상태 확인
make -f Makefile.dev dev-vllm-logs        # 로그 확인

# 전체
make -f Makefile.dev dev-start            # 모든 서비스 시작
make -f Makefile.dev dev-stop             # 모든 서비스 중지
make -f Makefile.dev dev-status           # 전체 상태 확인
```

## 🔍 현재 설정 확인

```bash
# 환경변수 확인
cat .env | grep VLLM

# 실행 중인 컨테이너 확인
docker compose ps vllm

# 로그 확인
docker compose logs vllm --tail 50
```

## ⚠️ 주의사항

### GPU 모드
- NVIDIA GPU 필요
- nvidia-container-toolkit 설치 필요
- GPU 메모리가 부족하면 OOM 에러 발생 가능

### CPU 모드
- ⚠️ 매우 느림 (응답 시간 수십 초 ~ 수분)
- RAM 8GB+ 권장
- ⚠️ vLLM CPU 모드는 실험적 기능
- 💡 CPU 모드가 작동하지 않으면 `DEV_MODE=true` 사용 권장

## 🐛 문제 해결

### GPU를 감지하지 못할 때

```bash
# GPU 확인
nvidia-smi

# Docker GPU 지원 확인
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi

# nvidia-container-toolkit 설치 필요
```

### CPU 모드가 작동하지 않을 때

vLLM의 CPU 모드가 작동하지 않으면 다음 옵션을 사용하세요:

**옵션 1: DEV_MODE 사용 (권장)**
```bash
# .env 파일에 추가
DEV_MODE=true

# API 서버 재시작
docker compose restart api
```

**옵션 2: 외부 LLM 서버 사용**
- Ollama (로컬 CPU 모드 지원)
- LM Studio (로컬 CPU 모드 지원)

### CPU 모드가 너무 느릴 때

- 더 작은 모델 사용 (이미 최소 모델 사용 중)
- 컨텍스트 길이 줄이기 (VLLM_MAX_MODEL_LEN=1024)
- DEV_MODE=true로 Mock 응답 사용

### OOM (Out of Memory) 에러

```bash
# 더 작은 모델 사용
VLLM_MODEL=Qwen/Qwen2.5-Coder-1.5B-Instruct

# GPU 메모리 사용률 낮추기
VLLM_GPU_MEMORY=0.7

# 컨텍스트 길이 줄이기
VLLM_MAX_MODEL_LEN=4096
```

## 📚 관련 문서

- [모델 선택 가이드](./vllm-model-selection.md)
- [GPU 설정 가이드](./vllm-gpu-setup.md)
- [설정 예시](./vllm-config-examples.md)
