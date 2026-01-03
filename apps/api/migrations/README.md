# 데이터베이스 마이그레이션 가이드

## 개요

이 프로젝트는 [Alembic](https://alembic.sqlalchemy.org/)을 사용하여 데이터베이스 스키마 버전을 관리합니다.

## 설정

### 환경변수

```bash
# 필수 환경변수
export DATABASE_URL="postgresql://cursor:cursor@localhost:5432/cursor_poc"

# 또는 .env 파일에 추가
echo 'DATABASE_URL=postgresql://cursor:cursor@localhost:5432/cursor_poc' >> .env
```

## 기본 명령어

### 마이그레이션 상태 확인

```bash
cd apps/api
alembic current          # 현재 버전 확인
alembic history          # 전체 마이그레이션 이력
```

### 새 마이그레이션 생성

```bash
# 자동 생성 (모델 변경 감지)
alembic revision --autogenerate -m "Add new feature"

# 수동 생성 (빈 마이그레이션)
alembic revision -m "Custom migration"
```

### 마이그레이션 적용

```bash
# 최신 버전으로 업그레이드
alembic upgrade head

# 특정 버전으로 업그레이드
alembic upgrade <revision_id>

# 한 단계씩 업그레이드
alembic upgrade +1
```

### 마이그레이션 롤백

```bash
# 한 단계 롤백
alembic downgrade -1

# 특정 버전으로 롤백
alembic downgrade <revision_id>

# 처음으로 롤백 (모든 테이블 삭제)
alembic downgrade base
```

### SQL 스크립트 생성 (오프라인)

```bash
# SQL 스크립트로 출력 (DB 연결 없이)
alembic upgrade head --sql > migration.sql
```

## 인덱스 최적화

이 프로젝트는 다음과 같은 최적화된 인덱스를 사용합니다:

### workspaces 테이블

| 인덱스 | 컬럼 | 용도 |
|--------|------|------|
| `idx_workspace_owner_status` | owner_id, status | 소유자별 워크스페이스 조회 |
| `idx_workspace_org_status` | org_id, status | 조직별 워크스페이스 조회 |
| `idx_workspace_last_accessed_status` | status, last_accessed_at | 자동 정지 대상 조회 |
| `idx_workspace_owner_created` | owner_id, created_at | 소유자별 생성일 정렬 |

### audit_logs 테이블

| 인덱스 | 컬럼 | 용도 |
|--------|------|------|
| `idx_audit_user_time` | user_id, timestamp | 사용자별 시간순 조회 |
| `idx_audit_workspace_time` | workspace_id, timestamp | 워크스페이스별 시간순 조회 |
| `idx_audit_action` | action | 액션별 필터링 |
| `idx_audit_action_time` | action, timestamp | 액션별 시간순 조회 |
| `idx_audit_user_action` | user_id, action | 사용자별 액션 통계 |

## 주의사항

### 1. 마이그레이션 파일 수정 금지

이미 적용된 마이그레이션 파일은 절대 수정하지 마세요. 새로운 마이그레이션을 생성하세요.

### 2. 롤백 테스트

프로덕션 적용 전 롤백이 정상 동작하는지 테스트하세요:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### 3. 대용량 테이블 마이그레이션

대용량 테이블에 인덱스를 추가할 때는 `CONCURRENTLY` 옵션을 사용하세요:

```python
# 마이그레이션 파일에서
from alembic import op

def upgrade():
    op.execute("CREATE INDEX CONCURRENTLY idx_name ON table(column)")
```

### 4. 프로덕션 배포

```bash
# 1. 백업 생성
pg_dump -U cursor cursor_poc > backup_$(date +%Y%m%d).sql

# 2. 마이그레이션 적용
alembic upgrade head

# 3. 확인
alembic current
```

## 파일 구조

```
apps/api/
├── alembic.ini              # Alembic 설정
├── migrations/
│   ├── env.py               # 환경 설정
│   ├── script.py.mako       # 템플릿
│   ├── README.md            # 이 문서
│   └── versions/            # 마이그레이션 파일들
│       └── 2026_01_03_0001-initial_schema.py
└── src/
    └── db/
        ├── connection.py    # DB 연결 설정
        └── models.py        # SQLAlchemy 모델
```

## 트러블슈팅

### 마이그레이션이 적용되지 않음

```bash
# 현재 상태 확인
alembic current

# 강제 마킹 (주의: 실제 스키마 변경 없음)
alembic stamp head
```

### 충돌 해결

```bash
# 여러 개의 head가 있는 경우
alembic heads

# 병합
alembic merge -m "Merge heads" <rev1> <rev2>
```

### asyncpg vs psycopg2

- **asyncpg**: 애플리케이션 런타임용 (비동기)
- **psycopg2**: Alembic 마이그레이션용 (동기)

`env.py`에서 자동으로 URL을 변환합니다:
```python
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
```
