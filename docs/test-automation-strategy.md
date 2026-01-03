# 테스트 자동화 전략

**작성일**: 2026-01-03  
**버전**: 1.0

---

## 📋 개요

이 문서는 Cursor On-Prem PoC 프로젝트의 종합적인 테스트 자동화 전략을 설명합니다.

### 현재 상태
- **Backend**: pytest 기반 7개 테스트 파일
- **Frontend**: Vitest 기반 2개 테스트 파일
- **CI/CD**: GitHub Actions (ci.yml, cd.yml)

### 목표
- 코드 커버리지 80% 이상
- 모든 PR에서 자동 테스트 실행
- 회귀 테스트 자동화
- 성능 테스트 통합

---

## 🏗️ 테스트 피라미드

```
                    ┌─────────────┐
                    │   E2E       │  ← 10%
                    │   Tests     │
                    ├─────────────┤
                    │ Integration │  ← 30%
                    │    Tests    │
                    ├─────────────┤
                    │    Unit     │  ← 60%
                    │    Tests    │
                    └─────────────┘
```

---

## 🧪 테스트 유형별 전략

### 1. 단위 테스트 (Unit Tests)

#### Backend (Python/pytest)

**위치**: `apps/api/tests/`

**현재 테스트 파일**:
- `test_rbac.py` - 역할/권한 테스트
- `test_ai_gateway.py` - AI Gateway 테스트
- `test_ide.py` - IDE 컨테이너 API 테스트
- `test_diff_utils.py` - Diff 유틸리티 테스트
- `test_filesystem.py` - 파일시스템 유틸리티 테스트
- `test_container_api.py` - 컨테이너 API 테스트
- `test_workspace_manager.py` - 워크스페이스 관리 테스트

**추가 필요 테스트**:
```python
# tests/test_auth.py - 인증 서비스
# tests/test_context_builder.py - 컨텍스트 빌더
# tests/test_audit_service.py - 감사 로깅
# tests/test_config.py - 설정 관리
```

**실행 방법**:
```bash
cd apps/api
pytest tests/ -v --cov=src --cov-report=html
```

#### Frontend (TypeScript/Vitest)

**위치**: `apps/web/src/__tests__/`

**현재 테스트 파일**:
- `api.test.ts` - API 클라이언트 테스트

**추가 필요 테스트**:
```typescript
// __tests__/components/AIChat.test.tsx
// __tests__/components/FileTree.test.tsx
// __tests__/hooks/useAuth.test.ts
// __tests__/lib/websocket.test.ts
```

**실행 방법**:
```bash
cd apps/web
pnpm test
pnpm test:coverage
```

---

### 2. 통합 테스트 (Integration Tests)

#### API 통합 테스트

**위치**: `apps/api/tests/integration/`

```python
# tests/integration/test_api_flow.py
"""
API 통합 테스트 - 전체 플로우
"""
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_full_workspace_flow(client):
    """워크스페이스 생성 → 파일 작성 → AI 분석 → 삭제 플로우"""
    # 1. 워크스페이스 생성
    resp = await client.post("/api/workspaces", json={
        "workspace_id": "test-ws",
        "name": "Test Workspace"
    })
    assert resp.status_code == 201
    
    # 2. 파일 생성
    resp = await client.post("/api/files/test-ws", json={
        "path": "main.py",
        "content": "print('hello')"
    })
    assert resp.status_code == 200
    
    # 3. AI 설명 요청
    resp = await client.post("/api/ai/explain", json={
        "workspace_id": "test-ws",
        "file_path": "main.py",
        "code": "print('hello')"
    })
    assert resp.status_code == 200
    
    # 4. 정리
    resp = await client.delete("/api/workspaces/test-ws")
    assert resp.status_code == 200
```

#### 데이터베이스 통합 테스트

```python
# tests/integration/test_database.py
"""
데이터베이스 통합 테스트
"""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc_test"
    )
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.mark.asyncio
async def test_user_crud(db_session):
    """사용자 CRUD 테스트"""
    from src.db.models import UserModel
    
    user = UserModel(user_id="test-user", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    
    result = await db_session.get(UserModel, "test-user")
    assert result is not None
    assert result.email == "test@example.com"
```

---

### 3. E2E 테스트 (End-to-End Tests)

#### Playwright 설정

```bash
# 설치
cd apps/web
pnpm add -D @playwright/test
npx playwright install
```

```typescript
// apps/web/e2e/workspace.spec.ts
import { test, expect } from '@playwright/test';

test.describe('워크스페이스 관리', () => {
  test.beforeEach(async ({ page }) => {
    // 로그인
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password');
    await page.click('button[type="submit"]');
  });

  test('워크스페이스 생성', async ({ page }) => {
    await page.goto('/dashboard');
    await page.click('text=새 워크스페이스');
    await page.fill('[name="name"]', 'Test Project');
    await page.click('text=생성');
    
    await expect(page.locator('text=Test Project')).toBeVisible();
  });

  test('AI 채팅', async ({ page }) => {
    await page.goto('/workspace/test-ws');
    
    // AI 채팅 입력
    await page.fill('[placeholder*="AI에게 질문"]', '이 코드를 설명해줘');
    await page.click('button[aria-label="전송"]');
    
    // 응답 대기
    await expect(page.locator('.ai-response')).toBeVisible({ timeout: 30000 });
  });

  test('WebIDE 실행', async ({ page }) => {
    await page.goto('/workspace/test-ws');
    await page.click('text=WebIDE 열기');
    
    // code-server 로드 확인
    await expect(page.locator('.monaco-editor')).toBeVisible({ timeout: 60000 });
  });
});
```

---

### 4. 성능 테스트

#### Locust 설정

```python
# tests/performance/locustfile.py
"""
성능 테스트 (Locust)
"""
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # 로그인
        resp = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password"
        })
        self.token = resp.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def list_workspaces(self):
        self.client.get("/api/workspaces", headers=self.headers)
    
    @task(2)
    def get_file_tree(self):
        self.client.get("/api/files/test-ws/tree", headers=self.headers)
    
    @task(1)
    def ai_explain(self):
        self.client.post("/api/ai/explain", 
            headers=self.headers,
            json={
                "workspace_id": "test-ws",
                "file_path": "main.py",
                "code": "print('hello')"
            }
        )
```

**실행 방법**:
```bash
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

---

## 🔄 CI/CD 통합

### GitHub Actions 워크플로우 개선

```yaml
# .github/workflows/ci.yml (개선안)
name: CI

on:
  push:
    branches: [main, develop, feature/*]
  pull_request:
    branches: [main, develop]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # 1단계: 코드 품질 검사
  code-quality:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install linters
        run: pip install ruff black mypy
      
      - name: Run Ruff
        run: ruff check apps/api/src/ --output-format=github
      
      - name: Run Black
        run: black --check apps/api/src/
      
      - name: Run MyPy
        run: mypy apps/api/src/ --ignore-missing-imports || true

  # 2단계: 단위 테스트
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: code-quality
    
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
        node-version: ['18', '20']
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: cursor_poc_test
        ports:
          - 5432:5432
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
      
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: --health-cmd "redis-cli ping" --health-interval 10s --health-timeout 5s --health-retries 5

    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      
      - name: Install Python dependencies
        run: |
          cd apps/api
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov httpx
      
      - name: Run Python tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc_test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test-secret-key
          DEV_MODE: "true"
        run: |
          cd apps/api
          pytest tests/ -v --cov=src --cov-report=xml --cov-report=html
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: apps/api/coverage.xml
          flags: backend
      
      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      
      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8
      
      - name: Install frontend dependencies
        run: pnpm install --frozen-lockfile
      
      - name: Run frontend tests
        run: |
          cd apps/web
          pnpm test:coverage
      
      - name: Upload frontend coverage
        uses: codecov/codecov-action@v4
        with:
          files: apps/web/coverage/lcov.info
          flags: frontend

  # 3단계: 통합 테스트
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: cursor_poc_test
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd apps/api
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc_test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET_KEY: test-secret-key
        run: |
          cd apps/api
          pytest tests/integration/ -v --tb=short

  # 4단계: E2E 테스트
  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 8
      
      - name: Install dependencies
        run: pnpm install --frozen-lockfile
      
      - name: Install Playwright
        run: npx playwright install --with-deps
      
      - name: Start services
        run: |
          docker compose -f docker-compose.test.yml up -d
          sleep 30
      
      - name: Run E2E tests
        run: |
          cd apps/web
          npx playwright test
      
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: apps/web/playwright-report/
      
      - name: Stop services
        if: always()
        run: docker compose -f docker-compose.test.yml down

  # 5단계: 보안 스캔
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: code-quality
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
      
      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Run Bandit (Python security)
        run: |
          pip install bandit
          bandit -r apps/api/src/ -f json -o bandit-report.json || true
      
      - name: Upload security reports
        uses: actions/upload-artifact@v4
        with:
          name: security-reports
          path: |
            bandit-report.json

  # 6단계: 빌드
  build:
    name: Build Images
    runs-on: ubuntu-latest
    needs: [unit-tests, security-scan]
    if: github.event_name == 'push'
    
    permissions:
      contents: read
      packages: write
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push API
        uses: docker/build-push-action@v5
        with:
          context: ./apps/api
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/api:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Build and push Web
        uses: docker/build-push-action@v5
        with:
          context: ./apps/web
          push: true
          tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/web:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## 📁 테스트 디렉토리 구조

```
apps/
├── api/
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py              # pytest 공통 fixture
│   │   ├── test_*.py                # 단위 테스트
│   │   ├── integration/             # 통합 테스트
│   │   │   ├── __init__.py
│   │   │   ├── test_api_flow.py
│   │   │   └── test_database.py
│   │   └── performance/             # 성능 테스트
│   │       └── locustfile.py
│   └── requirements-test.txt
│
└── web/
    ├── src/__tests__/               # 단위 테스트
    │   ├── api.test.ts
    │   ├── components/
    │   └── hooks/
    ├── e2e/                         # E2E 테스트
    │   ├── workspace.spec.ts
    │   └── auth.spec.ts
    ├── vitest.config.ts
    └── playwright.config.ts
```

---

## 🛠️ 설정 파일

### pytest 설정

```ini
# apps/api/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short --cov=src --cov-report=term-missing
filterwarnings =
    ignore::DeprecationWarning
```

### conftest.py

```python
# apps/api/tests/conftest.py
"""
pytest 공통 fixture
"""
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from src.main import app
from src.db.connection import get_db

# 테스트용 DB URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc_test"

@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 fixture"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """테스트용 DB 세션"""
    engine = create_async_engine(TEST_DATABASE_URL)
    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """테스트용 HTTP 클라이언트"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def auth_headers():
    """인증된 요청을 위한 헤더"""
    # 테스트용 JWT 토큰 생성
    from src.services.jwt_auth_service import jwt_auth_service
    token = jwt_auth_service.create_token(user_id="test-user", role="developer")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
async def test_workspace(client, auth_headers):
    """테스트용 워크스페이스 생성"""
    resp = await client.post(
        "/api/workspaces",
        headers=auth_headers,
        json={"workspace_id": "test-ws", "name": "Test Workspace"}
    )
    yield "test-ws"
    # 정리
    await client.delete("/api/workspaces/test-ws", headers=auth_headers)
```

### Vitest 설정

```typescript
// apps/web/vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'src/__tests__/',
      ],
    },
    include: ['src/**/*.test.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### Playwright 설정

```typescript
// apps/web/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'playwright-report/results.json' }],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'pnpm dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## 📊 커버리지 목표

| 영역 | 현재 | 목표 | 우선순위 |
|------|------|------|----------|
| Backend Unit Tests | ~40% | 80% | P0 |
| Frontend Unit Tests | ~20% | 70% | P1 |
| Integration Tests | ~10% | 50% | P1 |
| E2E Tests | 0% | 30% | P2 |
| Performance Tests | 0% | - | P3 |

---

## 🚀 실행 명령어 요약

```bash
# 전체 테스트 실행
make test

# Backend 테스트
cd apps/api && pytest tests/ -v --cov=src

# Frontend 테스트
cd apps/web && pnpm test

# E2E 테스트
cd apps/web && npx playwright test

# 성능 테스트
locust -f tests/performance/locustfile.py --host=http://localhost:8000

# 보안 스캔
bandit -r apps/api/src/
trivy fs .
```

---

## 📚 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [Vitest 공식 문서](https://vitest.dev/)
- [Playwright 공식 문서](https://playwright.dev/)
- [Locust 공식 문서](https://docs.locust.io/)
- [GitHub Actions 문서](https://docs.github.com/en/actions)
