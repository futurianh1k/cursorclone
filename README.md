# Cursor On-Prem PoC (Web) — Starter Repo

이 레포는 사내 온프레미스 환경에서 **웹 기반 Cursor-mini PoC**를 빠르게 착수하기 위한 스캐폴딩입니다.

## 구성
- `apps/web`: Next.js + Monaco 기반 Web IDE
- `apps/api`: FastAPI 기반 API 서버 (workspace/files/ai/patch/ws)
- `packages/shared-types`: API/WS DTO 타입 (TypeScript)
- `packages/diff-utils`: unified diff 파싱/검증/적용 유틸 (TypeScript)
- `packages/prompt-templates`: 프롬프트 템플릿
- `infra/llm`: vLLM 실행 예시 (온프레미스)

## Quickstart

빠른 시작 가이드는 [Quickstart 문서](docs/QUICKSTART.md)를 참조하세요.

### 빠른 시작 (요약)

```bash
# 1. 의존성 설치
pnpm -r install
cd apps/api && pip install -r requirements.txt

# 2. 워크스페이스 디렉토리 생성
sudo mkdir -p /workspaces && sudo chown $USER:$USER /workspaces

# 3. 서버 실행
# 터미널 1: API 서버
cd apps/api && uvicorn src.main:app --host 0.0.0.0 --port 8000

# 터미널 2: Web 서버
cd apps/web && pnpm dev
```

브라우저에서 `http://localhost:3000` 접속

### 로컬 개발 환경 (vLLM 포함)

개발자들이 로컬 PC에서 vLLM을 구동하는 방법:

```bash
# 1. GPU/CPU 자동 감지 및 설정
make -f Makefile.dev dev-vllm-setup

# 2. vLLM 서버 시작 (자동으로 GPU/CPU 모드 선택)
make -f Makefile.dev dev-vllm-start

# 3. 상태 확인
make -f Makefile.dev dev-vllm-status
```

**상세 가이드**: [로컬 개발 환경 설정](docs/dev-local-setup.md)

### Docker Compose로 실행
```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down
```

### 테스트 실행
```bash
cd apps/api
pytest tests/ -v
```

### 배포
```bash
# 개발 환경 배포
make deploy-dev

# 프로덕션 환경 배포
make deploy-prod

# Kubernetes 배포
make k8s-deploy
```

### 관리 도구
```bash
# Portainer (Docker 관리 UI)
make portainer
# 접속: http://localhost:9000

# Grafana (모니터링 대시보드)
make grafana
# 접속: http://localhost:3001 (admin/admin)

# 모든 관리 도구 시작
make tools
```

## 주요 기능

### ✅ 완료된 기능
- 워크스페이스 관리 (생성, 목록 조회, GitHub 클론)
- 파일 시스템 연동 (읽기, 쓰기, 트리 조회)
- Patch 검증 및 적용 (unified diff)
- Context Builder (프롬프트 생성)
- vLLM Router (LLM 통신)
- Web IDE (File Tree, Code Editor, AI Chat)
- 관리자 대시보드 (서버 관리, 인증 관리, 배치 정책)
- 인프라 서버 관리 (등록, 인증, 배치)

### 🔄 진행 중
- 워크스페이스 컨테이너 관리 구현
- 인프라 서버 실제 연결 구현
- 데이터베이스 마이그레이션 시스템

### 📋 다음 단계
- 워크스페이스 컨테이너 라이프사이클 관리
- 실제 서버 연결 및 리소스 수집
- 모니터링 대시보드 완성
- 보안 강화 (SSO/LDAP)

**상세 계획**: `docs/next-steps.md` 참조

## 아키텍처

```
Web IDE (Next.js + Monaco)
    ↓
API (FastAPI)
    ↓
Context Builder → vLLM Router → vLLM
    ↓
Patch Engine → File System
```

## 보안

- 경로 탈출 방지 (`../` 차단)
- 확장자 allowlist
- 파일 크기 제한
- 워크스페이스 격리
- 해시 기반 감사 로그 (원문 저장 안 함)

## 문서

### 시작하기
- **[Quickstart](docs/QUICKSTART.md)**: 빠른 시작 가이드 (필수 읽기)
- **[Architecture](docs/architecture.md)**: 시스템 아키텍처 개요

### 개발 문서
- **[API 명세](docs/api-spec.md)**: REST API 및 WebSocket 명세
- **[Context Builder](docs/context-builder.md)**: Context Builder 설계 및 구현

### 운영 문서
- **[운영 가이드](docs/runbook-onprem.md)**: 온프레미스 환경 운영 가이드
- **[DevOps 가이드](docs/devops-guide.md)**: CI/CD 및 배포 가이드

### 아키텍처 문서
- **[워크스페이스 컨테이너](docs/workspace-container-architecture.md)**: 컨테이너 기반 워크스페이스 설계
- **[스케일링 아키텍처](docs/scalability-architecture.md)**: 대규모 스케일링 (500명 규모)
- **[관리자 대시보드](docs/admin-dashboard-architecture.md)**: 관리자 대시보드 아키텍처

### 변경 이력
- `history/`: 프로젝트 변경 이력 문서

## 스케일링

이 프로젝트는 **500명 규모의 대규모 조직**을 위한 스케일링을 고려하여 설계되었습니다:

- **Stateless API**: 수평 확장 가능
- **비동기 데이터베이스**: 연결 풀 및 비동기 쿼리
- **Redis 캐싱**: 성능 최적화
- **멀티 테넌트**: 조직/팀별 격리 지원
- **Kubernetes 준비**: 컨테이너 기반 워크스페이스 (향후 구현)

상세 설계는 `docs/scalability-architecture.md` 참조

## Codex 작업
- `AGENTS.md` 규칙을 읽고 작업하도록 설정되어 있습니다.
- `codex/tasks/`에 Task 프롬프트가 준비되어 있습니다.
