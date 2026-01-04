# vLLM 자동 감지 가이드

## 🔍 자동 감지 동작 방식

현재 구현된 자동 감지는 **두 가지 방식**으로 동작합니다:

### 방식 1: Makefile 사용 시 (권장)

```bash
# Makefile.dev 사용 시 자동 감지됨
make -f Makefile.dev dev-vllm-start
```

**동작 순서:**
1. `auto-detect-vllm.sh` 스크립트 실행 (GPU/CPU 감지)
2. `.env` 파일에 설정 자동 생성/업데이트
3. GPU/CPU 모드에 따라 적절한 docker-compose 파일 선택
4. vLLM 서버 시작

### 방식 2: docker compose 직접 사용 시

**현재 상태**: 자동 감지되지 않음 ❌

```bash
# 이 명령어는 자동 감지하지 않음
docker compose up -d
```

**해결 방법:**

#### 옵션 A: Makefile 사용 (권장)
```bash
make -f Makefile.dev dev-start
```

#### 옵션 B: 수동으로 감지 스크립트 실행
```bash
# 1. 자동 감지 및 설정
./scripts/auto-detect-vllm.sh

# 2. docker compose 실행
docker compose up -d
```

#### 옵션 C: Wrapper 스크립트 사용
```bash
# docker-compose-wrapper.sh 사용 (향후 구현 예정)
./scripts/docker-compose-wrapper.sh up -d
```

## 📋 자동 감지 스크립트

### `scripts/auto-detect-vllm.sh`

**기능:**
- GPU/CPU 자동 감지
- 적절한 모델 선택
- `.env` 파일 자동 생성/업데이트
- 조용히 실행 (출력 최소화)

**호출 시점:**
- `make -f Makefile.dev dev-vllm-start` 실행 시
- `make docker-up` 실행 시 (Makefile에 추가됨)
- 수동 실행 가능

### `scripts/setup-dev-vllm.sh`

**기능:**
- GPU/CPU 자동 감지
- 사용자에게 확인 요청
- 상세한 정보 출력
- `.env` 파일 생성/업데이트

**호출 시점:**
- 초기 설정 시 (수동 실행)
- `make -f Makefile.dev dev-vllm-setup` 실행 시

## 🚀 완전 자동화를 위한 개선 방안

### 현재 한계

Docker Compose는 컨테이너 내부에서만 실행되므로, 호스트의 GPU를 직접 감지할 수 없습니다. 따라서:

1. **컨테이너 시작 전**에 호스트에서 감지 스크립트 실행 필요
2. **docker compose up** 명령어 자체를 래핑해야 함

### 권장 사용 방법

#### 방법 1: Makefile 사용 (가장 간단)

```bash
# 모든 서비스 시작 (자동 감지 포함)
make -f Makefile.dev dev-start

# vLLM만 시작 (자동 감지 포함)
make -f Makefile.dev dev-vllm-start
```

#### 방법 2: 빠른 시작 스크립트 사용

```bash
# 모든 서비스 자동 시작 (자동 감지 포함)
./scripts/quick-start-dev.sh
```

#### 방법 3: 수동 설정 후 docker compose 사용

```bash
# 1. 한 번만 설정 (초기 설정)
make -f Makefile.dev dev-vllm-setup

# 2. 이후에는 docker compose 직접 사용 가능
docker compose up -d
```

## 🔧 docker compose up 시 완전 자동화

완전 자동화를 원한다면 다음 중 하나를 선택:

### 옵션 1: Makefile을 기본으로 사용

```bash
# .bashrc 또는 .zshrc에 추가
alias docker-compose='make -f Makefile.dev dev-start'
```

### 옵션 2: Wrapper 스크립트 사용

```bash
# docker-compose-wrapper.sh를 PATH에 추가하거나
# docker-compose 명령어로 심볼릭 링크 생성
ln -s $(pwd)/scripts/docker-compose-wrapper.sh /usr/local/bin/docker-compose-dev
```

### 옵션 3: Git Hook 사용 (고급)

```bash
# .git/hooks/post-checkout 또는 pre-commit에 추가
./scripts/auto-detect-vllm.sh
```

## 📝 요약

| 명령어 | 자동 감지 여부 | 설명 |
|--------|--------------|------|
| `make -f Makefile.dev dev-vllm-start` | ✅ 예 | 자동 감지 및 시작 |
| `make docker-up` | ✅ 예 | Makefile에 추가됨 |
| `./scripts/quick-start-dev.sh` | ✅ 예 | 모든 서비스 자동 시작 |
| `docker compose up -d` | ❌ 아니오 | 수동 설정 필요 |
| `./scripts/auto-detect-vllm.sh && docker compose up -d` | ✅ 예 | 수동 실행 |

## 💡 권장 워크플로우

### 초기 설정 (한 번만)

```bash
# GPU/CPU 감지 및 설정
make -f Makefile.dev dev-vllm-setup
```

### 일상적인 사용

```bash
# 방법 1: Makefile 사용 (권장)
make -f Makefile.dev dev-start

# 방법 2: 빠른 시작 스크립트
./scripts/quick-start-dev.sh

# 방법 3: docker compose 직접 사용 (설정이 이미 있는 경우)
docker compose up -d
```

