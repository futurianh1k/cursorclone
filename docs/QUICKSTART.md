# Quickstart 가이드

이 문서는 Cursor On-Prem PoC를 빠르게 시작하는 방법을 안내합니다.

## 목차

1. [필수 요구사항](#필수-요구사항)
2. [설치](#설치)
3. [로컬 개발 환경 설정](#로컬-개발-환경-설정)
4. [Docker Compose로 실행](#docker-compose로-실행)
5. [첫 워크스페이스 사용](#첫-워크스페이스-사용)
6. [문제 해결](#문제-해결)

---

## 필수 요구사항

### 시스템 요구사항

- **OS**: Linux (Ubuntu 20.04+ 권장), macOS, Windows (WSL2)
- **Node.js**: 20.x 이상
- **pnpm**: 9.x 이상 (`npm install -g pnpm`)
- **Python**: 3.11 이상
- **Docker**: 20.x 이상 (선택사항, Docker Compose 사용 시)
- **Git**: 최신 버전

### 하드웨어 요구사항

**최소 사양**:
- CPU: 2 cores
- RAM: 4GB
- 디스크: 10GB 여유 공간

**권장 사양** (개발 환경):
- CPU: 4 cores
- RAM: 8GB
- 디스크: 20GB 여유 공간

**프로덕션 환경**:
- CPU: 8+ cores
- RAM: 16GB+
- 디스크: 50GB+ (워크스페이스 저장용)

---

## 설치

### 1. 저장소 클론

```bash
git clone <repository-url>
cd cursor-onprem-poc
```

### 2. Node.js 의존성 설치

```bash
pnpm -r install
```

이 명령은 모든 패키지의 의존성을 설치합니다:
- `apps/web`: Next.js 웹 애플리케이션
- `apps/api`: FastAPI 백엔드 (의존성만, Python 패키지는 별도 설치)
- `packages/shared-types`: 공유 타입 정의
- `packages/diff-utils`: Diff 유틸리티
- `packages/prompt-templates`: 프롬프트 템플릿

### 3. Python 의존성 설치

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

### 4. 환경 변수 설정

API 서버용 환경 변수 파일 생성:

```bash
cd apps/api
cp .env.example .env  # 파일이 있다면
```

필수 환경 변수:

```bash
# .env 파일
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cursor_poc
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here-change-in-production
VLLM_BASE_URL=http://localhost:8000/v1  # vLLM 서버 주소
```

---

## 로컬 개발 환경 설정

### 1. 워크스페이스 디렉토리 생성

워크스페이스는 `/workspaces` 디렉토리에 저장됩니다:

```bash
sudo mkdir -p /workspaces
sudo chown $USER:$USER /workspaces
```

**개발 모드 (선택사항)**:
개발 중에는 샘플 저장소를 사용할 수 있습니다:

```bash
# ~/cctv-fastapi 같은 샘플 저장소가 있다면
export DEV_MODE=true
```

### 2. 데이터베이스 설정

PostgreSQL과 Redis가 필요합니다.

**Docker로 실행** (권장):
```bash
docker run -d --name postgres \
  -e POSTGRES_USER=cursor_poc \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=cursor_poc \
  -p 5432:5432 \
  postgres:15

docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

**로컬 설치**:
- PostgreSQL: https://www.postgresql.org/download/
- Redis: https://redis.io/download

### 3. 데이터베이스 마이그레이션

```bash
cd apps/api
# 마이그레이션 스크립트가 있다면
./scripts/migrate-db.sh up
```

### 4. 서버 실행

**터미널 1: API 서버**

```bash
cd apps/api

# 개발 모드 (선택사항)
export DEV_MODE=true

# 서버 시작
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

API 서버가 `http://localhost:8000`에서 실행됩니다.
- API 문서: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**터미널 2: Web 서버**

```bash
cd apps/web
pnpm dev
```

Web 서버가 `http://localhost:3000`에서 실행됩니다.

---

## Docker Compose로 실행

전체 스택을 Docker Compose로 한 번에 실행할 수 있습니다.

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일 수정
```

### 2. 서비스 시작

```bash
# 빌드 및 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 특정 서비스 로그만
docker-compose logs -f api
docker-compose logs -f web
```

### 3. 서비스 중지

```bash
docker-compose down

# 볼륨까지 삭제
docker-compose down -v
```

### 4. 서비스 재시작

```bash
docker-compose restart

# 특정 서비스만
docker-compose restart api
```

---

## 첫 워크스페이스 사용

### 1. 브라우저 접속

브라우저에서 `http://localhost:3000` 접속

### 2. 워크스페이스 생성

**방법 1: GitHub 클론**

1. 워크스페이스 생성 화면에서 "GitHub에서 클론" 선택
2. GitHub 저장소 URL 입력 (예: `https://github.com/user/repo`)
3. 워크스페이스 이름 입력
4. "생성" 클릭

**방법 2: 빈 워크스페이스 생성**

1. "새 워크스페이스 생성" 선택
2. 워크스페이스 이름 입력
3. 언어 선택 (Python, JavaScript 등)
4. "생성" 클릭

### 3. 파일 탐색

- 왼쪽 사이드바에서 파일 트리 확인
- 파일 클릭하여 에디터에서 열기
- 디렉토리 클릭하여 확장/축소

### 4. 코드 편집

- Monaco Editor에서 코드 편집
- 언어 자동 감지 및 문법 하이라이팅
- 파일 저장: `Ctrl+S` (또는 `Cmd+S`)

### 5. AI 코드 수정

1. 코드 선택 (드래그)
2. 오른쪽 AI Chat 패널에서 지시사항 입력
   - 예: "이 함수를 더 효율적으로 리팩토링해줘"
   - 예: "이 코드에 에러 처리를 추가해줘"
3. "코드 수정" 버튼 클릭
4. Diff Preview 확인
5. "적용" 버튼 클릭하여 패치 적용

---

## 문제 해결

### API 서버가 시작되지 않음

**문제**: `ModuleNotFoundError` 또는 import 오류

**해결**:
```bash
cd apps/api
pip install -r requirements.txt
```

### Web 서버가 시작되지 않음

**문제**: 포트 3000이 이미 사용 중

**해결**:
```bash
# 포트 변경
cd apps/web
PORT=3001 pnpm dev
```

또는 다른 프로세스 종료:
```bash
lsof -ti:3000 | xargs kill -9
```

### 데이터베이스 연결 오류

**문제**: `Connection refused` 또는 `Authentication failed`

**해결**:
1. PostgreSQL/Redis가 실행 중인지 확인
2. `.env` 파일의 연결 정보 확인
3. 방화벽 설정 확인

### 워크스페이스가 보이지 않음

**문제**: 워크스페이스 목록이 비어있음

**해결**:
1. `/workspaces` 디렉토리 권한 확인
2. API 서버 로그 확인
3. 개발 모드인 경우 `DEV_MODE=true` 설정 확인

### Patch 적용 실패

**문제**: "Conflict" 또는 "Invalid patch" 오류

**해결**:
1. 파일이 다른 곳에서 수정되었는지 확인
2. 선택한 코드가 정확한지 확인
3. Diff Preview를 다시 확인

---

## 다음 단계

- [아키텍처 문서](../docs/architecture.md) 읽기
- [API 명세](../docs/api-spec.md) 확인
- [운영 가이드](../docs/runbook-onprem.md) 참조
- [스케일링 가이드](../docs/scalability-architecture.md) 검토

---

## 추가 리소스

- **문서**: `docs/` 폴더
- **변경 이력**: `history/` 폴더
- **문제 리포트**: GitHub Issues
- **커뮤니티**: (커뮤니티 링크가 있다면)
