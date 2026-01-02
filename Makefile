.PHONY: help build up down restart logs clean test lint migrate

help: ## 도움말 표시
	@echo "사용 가능한 명령어:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Docker 이미지 빌드
	docker-compose build

up: ## 서비스 시작
	docker-compose up -d

down: ## 서비스 중지
	docker-compose down

restart: ## 서비스 재시작
	docker-compose restart

logs: ## 로그 확인
	docker-compose logs -f

clean: ## 컨테이너 및 볼륨 정리
	docker-compose down -v
	docker system prune -f

test: ## 테스트 실행
	cd apps/api && pytest tests/ -v
	cd apps/web && pnpm test || true

lint: ## 코드 린트
	cd apps/api && ruff check src/ || true
	cd apps/web && pnpm lint || true

migrate: ## 데이터베이스 마이그레이션
	./scripts/migrate-db.sh up

dev: ## 개발 모드 실행
	pnpm --filter @poc/api dev &
	pnpm --filter @poc/web dev

deploy-dev: ## 개발 환경 배포
	./scripts/deploy.sh development deploy

deploy-prod: ## 프로덕션 환경 배포
	./scripts/deploy.sh production deploy

k8s-deploy: ## Kubernetes 배포
	./scripts/k8s-deploy.sh deploy

k8s-status: ## Kubernetes 상태 확인
	./scripts/k8s-deploy.sh status

monitoring: ## 모니터링 서비스 시작
	docker-compose --profile monitoring up -d prometheus grafana

tools: ## 관리 도구 시작 (Portainer, Grafana)
	docker-compose up -d portainer grafana

portainer: ## Portainer 시작
	docker-compose up -d portainer

grafana: ## Grafana 시작
	docker-compose up -d grafana
