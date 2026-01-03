# ============================================================
# Cursor On-Prem PoC - Makefile
# ============================================================
# 
# 개발, 테스트, 배포 자동화를 위한 명령어 모음
#
# 사용법:
#   make help       - 도움말 표시
#   make test       - 전체 테스트 실행
#   make dev        - 개발 서버 실행
#

.PHONY: help install dev test test-backend test-frontend test-e2e lint format clean docker-build docker-up docker-down

# 기본 타겟
.DEFAULT_GOAL := help

# ============================================================
# 도움말
# ============================================================

help:
	@echo "Cursor On-Prem PoC - 개발 명령어"
	@echo ""
	@echo "설치:"
	@echo "  make install        - 모든 의존성 설치"
	@echo "  make install-dev    - 개발 의존성 포함 설치"
	@echo ""
	@echo "개발:"
	@echo "  make dev            - 개발 서버 실행 (API + Web)"
	@echo "  make dev-api        - API 서버만 실행"
	@echo "  make dev-web        - Web 서버만 실행"
	@echo ""
	@echo "테스트:"
	@echo "  make test           - 전체 테스트 실행"
	@echo "  make test-backend   - Backend 테스트만"
	@echo "  make test-frontend  - Frontend 테스트만"
	@echo "  make test-e2e       - E2E 테스트"
	@echo "  make test-coverage  - 커버리지 리포트 생성"
	@echo ""
	@echo "코드 품질:"
	@echo "  make lint           - 린트 검사"
	@echo "  make format         - 코드 포맷팅"
	@echo "  make typecheck      - 타입 검사"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   - Docker 이미지 빌드"
	@echo "  make docker-up      - 서비스 시작"
	@echo "  make docker-down    - 서비스 중지"
	@echo "  make docker-logs    - 로그 확인"
	@echo ""
	@echo "기타:"
	@echo "  make clean          - 캐시/임시 파일 삭제"
	@echo "  make db-migrate     - DB 마이그레이션 실행"

# ============================================================
# 설치
# ============================================================

install:
	@echo "📦 의존성 설치 중..."
	pnpm install
	cd apps/api && pip install -r requirements.txt

install-dev: install
	@echo "🔧 개발 의존성 설치 중..."
	cd apps/api && pip install -r requirements-dev.txt || pip install pytest pytest-asyncio pytest-cov httpx ruff black mypy
	cd apps/web && pnpm add -D @playwright/test
	npx playwright install

# ============================================================
# 개발 서버
# ============================================================

dev:
	@echo "🚀 개발 서버 시작..."
	docker compose up -d db redis
	@sleep 3
	$(MAKE) -j2 dev-api dev-web

dev-api:
	@echo "🐍 API 서버 시작 (포트 8000)..."
	cd apps/api && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dev-web:
	@echo "⚛️ Web 서버 시작 (포트 3000)..."
	cd apps/web && pnpm dev

# ============================================================
# 테스트
# ============================================================

test: test-backend test-frontend
	@echo "✅ 전체 테스트 완료"

test-backend:
	@echo "🧪 Backend 테스트 실행 중..."
	cd apps/api && pytest tests/ -v --tb=short

test-backend-cov:
	@echo "🧪 Backend 테스트 (커버리지) 실행 중..."
	cd apps/api && pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-frontend:
	@echo "🧪 Frontend 테스트 실행 중..."
	cd apps/web && pnpm test

test-frontend-cov:
	@echo "🧪 Frontend 테스트 (커버리지) 실행 중..."
	cd apps/web && pnpm test:coverage

test-e2e:
	@echo "🎭 E2E 테스트 실행 중..."
	cd apps/web && npx playwright test

test-e2e-ui:
	@echo "🎭 E2E 테스트 (UI 모드) 실행 중..."
	cd apps/web && npx playwright test --ui

test-coverage: test-backend-cov test-frontend-cov
	@echo "📊 커버리지 리포트 생성 완료"
	@echo "Backend: apps/api/htmlcov/index.html"
	@echo "Frontend: apps/web/coverage/index.html"

# ============================================================
# 코드 품질
# ============================================================

lint:
	@echo "🔍 린트 검사 중..."
	cd apps/api && ruff check src/ tests/
	cd apps/web && pnpm lint

lint-fix:
	@echo "🔧 린트 자동 수정 중..."
	cd apps/api && ruff check src/ tests/ --fix
	cd apps/web && pnpm lint --fix

format:
	@echo "✨ 코드 포맷팅 중..."
	cd apps/api && black src/ tests/
	cd apps/web && pnpm format || npx prettier --write "src/**/*.{ts,tsx}"

format-check:
	@echo "✨ 포맷 검사 중..."
	cd apps/api && black --check src/ tests/
	cd apps/web && pnpm format:check || npx prettier --check "src/**/*.{ts,tsx}"

typecheck:
	@echo "📝 타입 검사 중..."
	cd apps/api && mypy src/ --ignore-missing-imports || true
	cd apps/web && pnpm typecheck || npx tsc --noEmit

# ============================================================
# Docker
# ============================================================

docker-build:
	@echo "🐳 Docker 이미지 빌드 중..."
	docker compose build

docker-up:
	@echo "🚀 Docker 서비스 시작..."
	docker compose up -d

docker-up-webide:
	@echo "🚀 WebIDE 서비스 시작..."
	docker compose -f docker-compose.webide.yml up -d

docker-down:
	@echo "⏹️ Docker 서비스 중지..."
	docker compose down

docker-down-webide:
	@echo "⏹️ WebIDE 서비스 중지..."
	docker compose -f docker-compose.webide.yml down

docker-logs:
	docker compose logs -f

docker-logs-api:
	docker compose logs -f api

docker-logs-web:
	docker compose logs -f web

docker-clean:
	@echo "🧹 Docker 리소스 정리 중..."
	docker compose down -v --remove-orphans
	docker system prune -f

# ============================================================
# 데이터베이스
# ============================================================

db-migrate:
	@echo "🔄 DB 마이그레이션 실행..."
	cd apps/api && alembic upgrade head || echo "Alembic not configured"

db-rollback:
	@echo "⏪ DB 롤백..."
	cd apps/api && alembic downgrade -1 || echo "Alembic not configured"

db-reset:
	@echo "🗑️ DB 리셋..."
	docker compose down -v
	docker compose up -d db
	@sleep 5
	$(MAKE) db-migrate

# ============================================================
# 보안
# ============================================================

security-scan:
	@echo "🔒 보안 스캔 중..."
	cd apps/api && bandit -r src/ -f json -o bandit-report.json || true
	trivy fs . --severity HIGH,CRITICAL || true
	gitleaks detect --source . || true

# ============================================================
# 정리
# ============================================================

clean:
	@echo "🧹 캐시 및 임시 파일 삭제 중..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "✅ 정리 완료"

# ============================================================
# CI/CD
# ============================================================

ci-test:
	@echo "🔄 CI 테스트 실행 중..."
	$(MAKE) lint
	$(MAKE) test-backend-cov
	$(MAKE) test-frontend-cov

ci-build:
	@echo "🔄 CI 빌드 실행 중..."
	cd apps/web && pnpm build
	$(MAKE) docker-build
