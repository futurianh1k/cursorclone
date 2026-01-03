"""
Locust 부하 테스트

API 엔드포인트 부하 테스트 시나리오

실행 방법:
  # 로컬 (UI 모드)
  locust -f tests/locustfile.py --host=http://localhost:8000

  # 헤드리스 모드
  locust -f tests/locustfile.py --headless \
    --host=http://localhost:8000 \
    --users=50 \
    --spawn-rate=10 \
    --run-time=1m

참조:
- Locust 문서: https://docs.locust.io/
"""

from locust import HttpUser, task, between, tag
import json
import random
import string


def random_string(length: int = 8) -> str:
    """랜덤 문자열 생성"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


class APIUser(HttpUser):
    """
    일반 API 사용자 시나리오
    
    다양한 엔드포인트에 대한 부하 테스트
    """
    
    # 요청 사이 대기 시간 (초)
    wait_time = between(1, 3)
    
    # 인증 토큰
    access_token: str = None
    workspace_id: str = None
    
    def on_start(self):
        """
        테스트 시작 시 실행
        로그인하여 토큰 획득
        """
        # 테스트 사용자 로그인 시도
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": f"loadtest_{random_string()}@example.com",
                "password": "testpassword123"
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("accessToken")
            response.success()
        elif response.status_code == 401:
            # 인증 실패는 예상됨 (테스트 사용자 미등록)
            response.success()
        else:
            response.failure(f"Login failed: {response.status_code}")
    
    @property
    def auth_headers(self) -> dict:
        """인증 헤더"""
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}
    
    # ============================================================
    # Health Check (가장 가벼운 엔드포인트)
    # ============================================================
    
    @task(10)
    @tag("health")
    def health_check(self):
        """헬스 체크 엔드포인트"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    # ============================================================
    # 인증 관련
    # ============================================================
    
    @task(2)
    @tag("auth")
    def login_attempt(self):
        """로그인 시도 (실패 예상)"""
        with self.client.post(
            "/api/auth/login",
            json={
                "email": f"user_{random_string()}@example.com",
                "password": "wrongpassword"
            },
            catch_response=True
        ) as response:
            # 401은 정상적인 응답
            if response.status_code in [200, 401]:
                response.success()
            elif response.status_code == 429:
                # Rate limit
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    # ============================================================
    # 워크스페이스 관련
    # ============================================================
    
    @task(5)
    @tag("workspace")
    def list_workspaces(self):
        """워크스페이스 목록 조회"""
        with self.client.get(
            "/api/workspaces",
            headers=self.auth_headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"List workspaces failed: {response.status_code}")
    
    @task(3)
    @tag("workspace", "files")
    def get_file_tree(self):
        """파일 트리 조회"""
        workspace_id = self.workspace_id or "test-workspace"
        with self.client.get(
            f"/api/workspaces/{workspace_id}/files/tree",
            headers=self.auth_headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 404]:
                response.success()
            else:
                response.failure(f"Get file tree failed: {response.status_code}")
    
    # ============================================================
    # AI 관련 (무거운 엔드포인트)
    # ============================================================
    
    @task(1)
    @tag("ai")
    def ai_chat(self):
        """AI 채팅 요청"""
        workspace_id = self.workspace_id or "test-workspace"
        with self.client.post(
            "/api/ai/chat",
            json={
                "workspaceId": workspace_id,
                "message": "What is Python?",
                "mode": "ask"
            },
            headers=self.auth_headers,
            catch_response=True,
            timeout=30  # AI 응답은 시간이 걸릴 수 있음
        ) as response:
            if response.status_code in [200, 401, 404, 503]:
                response.success()
            else:
                response.failure(f"AI chat failed: {response.status_code}")


class AdminUser(HttpUser):
    """
    관리자 사용자 시나리오
    
    관리자 전용 엔드포인트 테스트
    """
    
    wait_time = between(2, 5)
    weight = 1  # 일반 사용자보다 적은 비율
    
    @task(5)
    @tag("admin", "health")
    def admin_health(self):
        """관리자 헬스 체크"""
        self.client.get("/health")
    
    @task(2)
    @tag("admin", "servers")
    def list_servers(self):
        """서버 목록 조회"""
        with self.client.get(
            "/api/admin/servers",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401, 403]:
                response.success()
            else:
                response.failure(f"List servers failed: {response.status_code}")


class HeavyAIUser(HttpUser):
    """
    AI 집중 사용자 시나리오
    
    AI 엔드포인트에 집중적인 부하 테스트
    """
    
    wait_time = between(5, 10)  # AI 요청은 간격을 둠
    weight = 1  # 낮은 비율
    
    @task
    @tag("ai", "heavy")
    def ai_explain(self):
        """AI 코드 설명 요청"""
        workspace_id = "test-workspace"
        with self.client.post(
            "/api/ai/explain",
            json={
                "workspaceId": workspace_id,
                "filePath": "main.py",
                "selection": {
                    "startLine": 1,
                    "endLine": 10
                }
            },
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code in [200, 401, 404, 503]:
                response.success()
            else:
                response.failure(f"AI explain failed: {response.status_code}")
    
    @task
    @tag("ai", "heavy")
    def ai_rewrite(self):
        """AI 코드 리라이트 요청"""
        workspace_id = "test-workspace"
        with self.client.post(
            "/api/ai/rewrite",
            json={
                "workspaceId": workspace_id,
                "instruction": "Add type hints",
                "target": {
                    "file": "main.py",
                    "selection": {
                        "startLine": 1,
                        "endLine": 10
                    }
                }
            },
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code in [200, 401, 404, 503]:
                response.success()
            else:
                response.failure(f"AI rewrite failed: {response.status_code}")


# ============================================================
# 성능 목표 (참고용)
# ============================================================
# 
# | 엔드포인트 | P50 | P95 | P99 |
# |-----------|-----|-----|-----|
# | GET /health | <10ms | <50ms | <100ms |
# | POST /api/auth/login | <100ms | <300ms | <500ms |
# | GET /api/workspaces | <50ms | <150ms | <300ms |
# | GET /api/workspaces/{id}/files/tree | <100ms | <300ms | <500ms |
# | POST /api/ai/chat | <5s | <10s | <15s |
# | POST /api/ai/explain | <5s | <10s | <15s |
# ============================================================
