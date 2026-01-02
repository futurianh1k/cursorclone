#!/bin/bash
set -e

# 배포 스크립트
# 사용법: ./scripts/deploy.sh [environment] [action]
# 예: ./scripts/deploy.sh production deploy

ENVIRONMENT=${1:-development}
ACTION=${2:-deploy}

echo "🚀 Deploying to ${ENVIRONMENT} environment..."

# 환경별 설정
case $ENVIRONMENT in
  development)
    COMPOSE_FILE="docker-compose.yml"
    ;;
  production)
    COMPOSE_FILE="docker-compose.prod.yml"
    ;;
  *)
    echo "❌ Unknown environment: ${ENVIRONMENT}"
    exit 1
    ;;
esac

# 액션별 실행
case $ACTION in
  deploy)
    echo "📦 Building and deploying..."
    docker-compose -f ${COMPOSE_FILE} build
    docker-compose -f ${COMPOSE_FILE} up -d
    
    echo "⏳ Waiting for services to be healthy..."
    sleep 10
    
    echo "✅ Deployment complete!"
    docker-compose -f ${COMPOSE_FILE} ps
    ;;
  
  update)
    echo "🔄 Updating services..."
    docker-compose -f ${COMPOSE_FILE} pull
    docker-compose -f ${COMPOSE_FILE} up -d --no-deps --build
    
    echo "✅ Update complete!"
    ;;
  
  rollback)
    echo "⏪ Rolling back..."
    docker-compose -f ${COMPOSE_FILE} down
    docker-compose -f ${COMPOSE_FILE} up -d
    
    echo "✅ Rollback complete!"
    ;;
  
  stop)
    echo "🛑 Stopping services..."
    docker-compose -f ${COMPOSE_FILE} down
    ;;
  
  logs)
    docker-compose -f ${COMPOSE_FILE} logs -f
    ;;
  
  *)
    echo "❌ Unknown action: ${ACTION}"
    echo "Available actions: deploy, update, rollback, stop, logs"
    exit 1
    ;;
esac
