#!/bin/bash
set -e

# 데이터베이스 마이그레이션 스크립트
# 사용법: ./scripts/migrate-db.sh [up|down|create]

ACTION=${1:-up}
DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc}

echo "🗄️  Database Migration: ${ACTION}"

case $ACTION in
  up)
    echo "⬆️  Running migrations..."
    cd apps/api
    python -c "
from src.db.connection import init_db
import asyncio

async def migrate():
    await init_db()
    print('✅ Migrations completed!')

asyncio.run(migrate())
"
    ;;
  
  down)
    echo "⚠️  Down migrations not implemented yet"
    echo "Please manually drop tables if needed"
    ;;
  
  create)
    echo "📝 Creating migration..."
    echo "⚠️  Auto-migration is enabled. Tables are created automatically on startup."
    ;;
  
  *)
    echo "❌ Unknown action: ${ACTION}"
    echo "Available actions: up, down, create"
    exit 1
    ;;
esac
