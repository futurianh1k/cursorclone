"""
pytest 공통 fixture

테스트 실행 전 공통 설정 및 fixture 정의
"""

import pytest
import asyncio
import os
from typing import AsyncGenerator
from unittest.mock import MagicMock, AsyncMock

# 테스트 환경 설정
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 fixture (세션 범위)"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """
    테스트용 DB 세션 (트랜잭션 롤백)
    
    각 테스트 후 자동으로 롤백되어 테스트 격리 보장
    """
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        test_db_url = os.getenv("DATABASE_URL")
        engine = create_async_engine(test_db_url)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            yield session
            await session.rollback()
    except ImportError:
        # DB 없이 테스트 실행 시 Mock 반환
        yield MagicMock()


@pytest.fixture
async def client():
    """
    테스트용 HTTP 클라이언트
    
    FastAPI TestClient를 사용하여 API 테스트
    """
    try:
        from httpx import AsyncClient
        from src.main import app
        
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    except ImportError:
        yield MagicMock()


@pytest.fixture
def auth_headers():
    """
    인증된 요청을 위한 헤더
    
    테스트용 JWT 토큰 생성
    """
    try:
        from src.services.jwt_auth_service import jwt_auth_service
        token = jwt_auth_service.create_token(
            user_id="test-user",
            role="developer",
        )
        return {"Authorization": f"Bearer {token}"}
    except ImportError:
        return {"Authorization": "Bearer test-token"}


@pytest.fixture
def admin_auth_headers():
    """관리자 권한 인증 헤더"""
    try:
        from src.services.jwt_auth_service import jwt_auth_service
        token = jwt_auth_service.create_token(
            user_id="admin-user",
            role="admin",
        )
        return {"Authorization": f"Bearer {token}"}
    except ImportError:
        return {"Authorization": "Bearer admin-test-token"}


@pytest.fixture
def mock_llm_client():
    """Mock LLM 클라이언트"""
    mock = AsyncMock()
    mock.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(content="Mock LLM response")
            )
        ],
        usage=MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
    )
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis 클라이언트"""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.incr.return_value = 1
    mock.expire.return_value = True
    return mock


@pytest.fixture
async def test_workspace(client, auth_headers):
    """
    테스트용 워크스페이스 생성 및 정리
    
    테스트 완료 후 자동 삭제
    """
    workspace_id = "test-ws-" + os.urandom(4).hex()
    
    # 워크스페이스 생성 (가능한 경우)
    try:
        resp = await client.post(
            "/api/workspaces",
            headers=auth_headers,
            json={
                "workspace_id": workspace_id,
                "name": "Test Workspace",
            }
        )
        if resp.status_code == 201:
            yield workspace_id
            # 정리
            await client.delete(f"/api/workspaces/{workspace_id}", headers=auth_headers)
        else:
            yield workspace_id
    except Exception:
        yield workspace_id


@pytest.fixture
def sample_python_code():
    """샘플 Python 코드"""
    return '''
def calculate_sum(numbers: list[int]) -> int:
    """숫자 리스트의 합계를 계산합니다."""
    total = 0
    for num in numbers:
        total += num
    return total

class Calculator:
    """간단한 계산기 클래스"""
    
    def __init__(self):
        self.result = 0
    
    def add(self, x: int) -> int:
        self.result += x
        return self.result
    
    def reset(self):
        self.result = 0
'''


@pytest.fixture
def sample_typescript_code():
    """샘플 TypeScript 코드"""
    return '''
interface User {
  id: string;
  name: string;
  email: string;
}

async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/api/users/${id}`);
  if (!response.ok) {
    throw new Error('User not found');
  }
  return response.json();
}

export class UserService {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
  
  async getUser(id: string): Promise<User> {
    return fetchUser(id);
  }
}
'''


# ============================================================
# pytest 설정
# ============================================================

def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )


def pytest_collection_modifyitems(config, items):
    """테스트 수집 시 마커 자동 추가"""
    for item in items:
        # 파일 경로에 따라 마커 추가
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
