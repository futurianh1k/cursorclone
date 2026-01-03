# 🔒 오프라인(에어갭) 환경 배포 가이드

> 이 문서는 외부 인터넷 연결이 완전히 차단된 환경(Air-Gap)에서 
> Cursor On-Prem PoC를 배포하는 방법을 설명합니다.

---

## 📋 목차

1. [개요](#개요)
2. [사전 준비 (온라인 환경)](#1-사전-준비-온라인-환경)
3. [오프라인 서버 설정](#2-오프라인-서버-설정)
4. [서비스 실행](#3-서비스-실행)
5. [검증](#4-검증)
6. [문제 해결](#5-문제-해결)

---

## 개요

### 아키텍처

```
┌─────────────────── 온프레미스 네트워크 (인터넷 차단) ─────────────────────┐
│                                                                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │  Web IDE    │ → │  API 서버   │ → │   vLLM      │                   │
│  │  (Next.js)  │    │  (FastAPI)  │    │  (GPU)      │                   │
│  │   :3000     │    │   :8000     │    │   :8001     │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│         │                 │                                               │
│         │           ┌─────┴─────┐                                        │
│         │           │           │                                        │
│         │    ┌──────┴───┐ ┌─────┴─────┐                                  │
│         │    │PostgreSQL│ │   Redis   │                                  │
│         │    │  :5432   │ │   :6379   │                                  │
│         │    └──────────┘ └───────────┘                                  │
│         │                                                                 │
│  ┌──────┴──────────────────────────────────────────────────────────┐     │
│  │                     Docker Host                                  │     │
│  │  - 모든 이미지: 사전 로드됨                                        │     │
│  │  - LLM 모델: 로컬 캐시                                            │     │
│  │  - 패키지: 오프라인 미러                                           │     │
│  └──────────────────────────────────────────────────────────────────┘     │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
                    ↓
             외부 인터넷 접근 불필요 ❌
```

### 필수 조건

| 항목 | 최소 사양 | 권장 사양 |
|------|-----------|-----------|
| CPU | 8코어 | 16코어+ |
| RAM | 32GB | 64GB+ |
| GPU | NVIDIA 16GB (RTX 4080) | NVIDIA 24GB+ (RTX 4090/A100) |
| 저장소 | 200GB SSD | 500GB+ NVMe |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

---

## 1. 사전 준비 (온라인 환경)

> ⚠️ 이 단계는 **인터넷 연결이 가능한 환경**에서 실행합니다.

### 1.1 Docker 이미지 다운로드

```bash
# 필수 이미지 다운로드
docker pull vllm/vllm-openai:latest
docker pull postgres:15-alpine
docker pull redis:7-alpine
docker pull nginx:1.25-alpine
docker pull gitea/gitea:1.21-rootless
docker pull ghcr.io/berriai/litellm:main-latest
docker pull quay.io/keycloak/keycloak:23.0

# 애플리케이션 이미지 (직접 빌드하거나 레지스트리에서 pull)
# docker pull ghcr.io/<your-org>/cursor-onprem-api:latest
# docker pull ghcr.io/<your-org>/cursor-onprem-web:latest
```

### 1.2 이미지를 파일로 저장

```bash
# 저장 디렉토리 생성
mkdir -p ./offline-package/images

# 개별 이미지 저장
docker save vllm/vllm-openai:latest -o ./offline-package/images/vllm.tar
docker save postgres:15-alpine -o ./offline-package/images/postgres.tar
docker save redis:7-alpine -o ./offline-package/images/redis.tar
docker save nginx:1.25-alpine -o ./offline-package/images/nginx.tar
docker save gitea/gitea:1.21-rootless -o ./offline-package/images/gitea.tar
docker save ghcr.io/berriai/litellm:main-latest -o ./offline-package/images/litellm.tar
docker save quay.io/keycloak/keycloak:23.0 -o ./offline-package/images/keycloak.tar

# 또는 모든 이미지를 하나의 파일로
docker save \
  vllm/vllm-openai:latest \
  postgres:15-alpine \
  redis:7-alpine \
  nginx:1.25-alpine \
  -o ./offline-package/images/all-images.tar
```

### 1.3 LLM 모델 다운로드

```bash
# HuggingFace CLI 설치 (필요시)
pip install huggingface-hub

# 모델 디렉토리 생성
mkdir -p ./offline-package/models

# Qwen2.5-Coder 모델 다운로드 (권장)
huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct \
  --local-dir ./offline-package/models/Qwen2.5-Coder-7B-Instruct

# GPU 메모리에 따른 대안 모델
# 8GB GPU용:
# huggingface-cli download Qwen/Qwen2.5-Coder-1.5B-Instruct \
#   --local-dir ./offline-package/models/Qwen2.5-Coder-1.5B-Instruct

# 24GB+ GPU용:
# huggingface-cli download Qwen/Qwen2.5-Coder-14B-Instruct \
#   --local-dir ./offline-package/models/Qwen2.5-Coder-14B-Instruct
```

### 1.4 프로젝트 소스 복사

```bash
# 프로젝트 소스 복사
cp -r /path/to/cursor-onprem-poc ./offline-package/source

# .env 예제 파일 복사
cp .env.example ./offline-package/source/.env.example
```

### 1.5 배포 패키지 생성

```bash
# 전체 패키지 압축
cd offline-package
tar -czvf cursor-onprem-offline-$(date +%Y%m%d).tar.gz \
  images/ \
  models/ \
  source/

# 패키지 크기 확인 (대략 20-50GB 예상)
ls -lh cursor-onprem-offline-*.tar.gz
```

### 1.6 USB/하드디스크로 전송

```bash
# USB 마운트 (예시)
sudo mount /dev/sdb1 /mnt/usb

# 패키지 복사
cp cursor-onprem-offline-*.tar.gz /mnt/usb/

# 체크섬 생성 (무결성 검증용)
sha256sum cursor-onprem-offline-*.tar.gz > /mnt/usb/checksum.txt

# 안전하게 언마운트
sudo umount /mnt/usb
```

---

## 2. 오프라인 서버 설정

> ⚠️ 이 단계부터는 **인터넷 연결이 없는 오프라인 환경**에서 실행합니다.

### 2.1 패키지 복사 및 압축 해제

```bash
# USB에서 복사
cp /mnt/usb/cursor-onprem-offline-*.tar.gz /opt/

# 체크섬 검증
sha256sum -c /mnt/usb/checksum.txt

# 압축 해제
cd /opt
tar -xzvf cursor-onprem-offline-*.tar.gz
```

### 2.2 Docker 이미지 로드

```bash
cd /opt/offline-package/images

# 개별 이미지 로드
docker load -i vllm.tar
docker load -i postgres.tar
docker load -i redis.tar
docker load -i nginx.tar
docker load -i gitea.tar
docker load -i litellm.tar
docker load -i keycloak.tar

# 또는 통합 파일에서 로드
# docker load -i all-images.tar

# 로드 확인
docker images
```

### 2.3 LLM 모델 배치

```bash
# 모델 디렉토리 생성
sudo mkdir -p /models

# 모델 복사
sudo cp -r /opt/offline-package/models/* /models/

# 권한 설정
sudo chmod -R 755 /models
```

### 2.4 프로젝트 설정

```bash
# 소스 복사
sudo cp -r /opt/offline-package/source /opt/cursor-onprem
cd /opt/cursor-onprem

# 환경변수 설정
cp .env.example .env

# .env 파일 편집
nano .env
```

### 2.5 환경변수 설정

```bash
# .env 파일 내용
# ============================================
# 데이터베이스
# ============================================
POSTGRES_USER=cursor
POSTGRES_PASSWORD=<강력한_비밀번호>
POSTGRES_DB=cursor_db
DATABASE_URL=postgresql+asyncpg://cursor:<비밀번호>@db:5432/cursor_db

# ============================================
# Redis
# ============================================
REDIS_URL=redis://redis:6379/0

# ============================================
# 인증
# ============================================
JWT_SECRET_KEY=<32자_이상_랜덤_문자열>
MASTER_ENCRYPTION_KEY=<32자_암호화_키>

# ============================================
# vLLM (오프라인 모델 사용)
# ============================================
VLLM_BASE_URL=http://vllm:8000/v1
VLLM_MODEL=/models/Qwen2.5-Coder-7B-Instruct

# ============================================
# CORS (내부 네트워크만)
# ============================================
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.100:3000

# ============================================
# 디버그 (프로덕션에서는 false)
# ============================================
DEBUG=false
```

---

## 3. 서비스 실행

### 3.1 Docker Compose로 실행

```bash
cd /opt/cursor-onprem

# 서비스 시작
docker compose -f docker-compose.yml up -d

# vLLM 서비스 시작 (GPU 필요)
docker compose -f docker-compose.vllm.yml up -d

# 로그 확인
docker compose logs -f
```

### 3.2 vLLM 오프라인 모드 설정

```yaml
# docker-compose.vllm.yml 수정
services:
  vllm:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - HF_HUB_OFFLINE=1  # 오프라인 모드 강제
      - TRANSFORMERS_OFFLINE=1  # Transformers 오프라인 모드
    volumes:
      - /models:/models:ro  # 로컬 모델 마운트
    command: >
      --model /models/Qwen2.5-Coder-7B-Instruct
      --host 0.0.0.0
      --port 8000
      --trust-remote-code
```

### 3.3 서비스 상태 확인

```bash
# 모든 컨테이너 상태 확인
docker compose ps

# 예상 출력:
# NAME                 STATUS          PORTS
# cursor-poc-api       Up (healthy)    0.0.0.0:8000->8000/tcp
# cursor-poc-web       Up (healthy)    0.0.0.0:3000->3000/tcp
# cursor-poc-db        Up (healthy)    5432/tcp
# cursor-poc-redis     Up (healthy)    6379/tcp
# cursor-poc-vllm      Up              0.0.0.0:8001->8000/tcp
```

---

## 4. 검증

### 4.1 네트워크 격리 확인

```bash
# 외부 연결 테스트 (실패해야 함)
curl -I https://google.com
# 예상: 타임아웃 또는 연결 거부

# 내부 서비스 테스트 (성공해야 함)
curl http://localhost:8000/health
# 예상: {"ok":true,"version":"0.1.0"}
```

### 4.2 LLM 동작 확인

```bash
# vLLM 직접 테스트
curl http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "/models/Qwen2.5-Coder-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello, write a Python hello world"}]
  }'
```

### 4.3 API 서버 테스트

```bash
# 건강 체크
curl http://localhost:8000/health/ready

# 인증 테스트
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Test1234!", "name": "Test User"}'
```

### 4.4 웹 UI 접속

브라우저에서 `http://<서버IP>:3000` 접속

---

## 5. 문제 해결

### 5.1 Docker 이미지 로드 실패

```bash
# 오류: Error loading image
# 해결: 체크섬 확인 후 재복사
sha256sum images.tar
# 원본과 비교하여 일치하지 않으면 USB에서 재복사
```

### 5.2 vLLM GPU 인식 안 됨

```bash
# NVIDIA 드라이버 확인
nvidia-smi

# Docker NVIDIA 런타임 확인
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# 드라이버 재설치 (오프라인 패키지 필요)
# 사전에 .run 파일 준비 필요
```

### 5.3 모델 로드 실패

```bash
# 로그 확인
docker logs cursor-poc-vllm

# 일반적인 원인:
# 1. 모델 경로 오류 → 볼륨 마운트 확인
# 2. GPU 메모리 부족 → 더 작은 모델 사용
# 3. 권한 문제 → chmod 755 /models
```

### 5.4 데이터베이스 연결 실패

```bash
# PostgreSQL 로그 확인
docker logs cursor-poc-db

# 연결 테스트
docker exec -it cursor-poc-db psql -U cursor -d cursor_db -c "SELECT 1"
```

---

## 📦 오프라인 패키지 체크리스트

```
offline-package/
├── images/                      # Docker 이미지 (~15GB)
│   ├── vllm.tar                # vLLM (~8GB)
│   ├── postgres.tar            # PostgreSQL (~200MB)
│   ├── redis.tar               # Redis (~50MB)
│   ├── nginx.tar               # Nginx (~50MB)
│   ├── gitea.tar               # Gitea (~200MB)
│   ├── litellm.tar             # LiteLLM (~500MB)
│   └── keycloak.tar            # Keycloak (~500MB)
│
├── models/                      # LLM 모델 (~15-30GB)
│   └── Qwen2.5-Coder-7B-Instruct/
│       ├── config.json
│       ├── model-*.safetensors
│       └── tokenizer.json
│
├── source/                      # 프로젝트 소스
│   ├── apps/
│   ├── docker/
│   ├── docker-compose.yml
│   └── .env.example
│
└── checksum.txt                 # SHA256 체크섬
```

---

## 🔐 보안 고려사항

1. **USB/하드디스크 보안**: 전송 매체 암호화 권장
2. **비밀번호 정책**: 최소 12자, 특수문자 포함
3. **네트워크 격리**: 물리적 네트워크 분리 확인
4. **접근 로그**: 모든 접근 시도 기록
5. **정기 백업**: 주 1회 이상 데이터 백업

---

*마지막 업데이트: 2026-01-03*
