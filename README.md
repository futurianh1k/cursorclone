# Cursor On-Prem PoC (Web) — Starter Repo

이 레포는 사내 온프레미스 환경에서 **웹 기반 Cursor-mini PoC**를 빠르게 착수하기 위한 스캐폴딩입니다.

## 구성
- `apps/web`: Next.js + Monaco 기반 Web IDE
- `apps/api`: FastAPI 기반 API 서버 (workspace/files/ai/patch/ws)
- `packages/shared-types`: API/WS DTO 타입 (TypeScript)
- `packages/diff-utils`: unified diff 파싱/검증/적용 유틸 (TypeScript)
- `packages/prompt-templates`: 프롬프트 템플릿
- `infra/llm`: vLLM 실행 예시 (온프레미스)

## Quickstart (개발자 PC 또는 사내 Dev 서버)

### 필수 요구사항
- Node 20+, pnpm, Python 3.11+

### 설치

#### Node.js 의존성
```bash
pnpm -r install
```

#### Python 의존성 (API 서버)

**방법 1: requirements.txt 사용 (권장)**
```bash
cd apps/api
pip install -r requirements.txt

# 개발 및 테스트 포함
pip install -r requirements-dev.txt
```

**방법 2: pyproject.toml 사용**
```bash
cd apps/api
pip install -e ".[test]"
```

### 실행

#### 1. 워크스페이스 디렉토리 생성

워크스페이스는 `/workspaces` 디렉토리에 저장됩니다:

```bash
sudo mkdir -p /workspaces
sudo chown $USER:$USER /workspaces
```

#### 2. 서버 실행

```bash
# 터미널 1: API 서버
cd apps/api
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 터미널 2: Web 서버
cd apps/web
pnpm dev
```

#### 3. 워크스페이스 사용

브라우저에서 `http://localhost:3000` 접속 후:
- **GitHub 클론**: GitHub 저장소 URL을 입력하여 클론
- **빈 워크스페이스 생성**: 새 워크스페이스 생성

브라우저에서 `http://localhost:3000` 접속

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

- `docs/architecture.md`: 시스템 아키텍처
- `docs/api-spec.md`: API 명세
- `docs/context-builder.md`: Context Builder 설계
- `docs/workspace-container-architecture.md`: 컨테이너 기반 워크스페이스 설계
- `docs/scalability-architecture.md`: 대규모 스케일링 아키텍처 (500명 규모)
- `docs/admin-dashboard-architecture.md`: 관리자 대시보드 아키텍처
- `docs/devops-guide.md`: CI/CD 및 배포 가이드
- `docs/runbook-onprem.md`: 온프레미스 운영 가이드
- `history/`: 변경 이력 문서

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
