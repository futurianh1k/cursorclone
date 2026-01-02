"""
컨테이너 API 엔드포인트 테스트

FastAPI TestClient를 사용한 API 통합 테스트

사용법:
    cd apps/api
    pytest tests/test_container_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.main import app
from src.models.container import (
    ContainerStatus,
    ContainerStatusResponse,
    ContainerLogsResponse,
    ExecuteCommandResponse,
)
from src.services.workspace_manager import WorkspaceManager, WorkspaceManagerError


@pytest.fixture
def client():
    """TestClient 인스턴스"""
    return TestClient(app)


@pytest.fixture
def mock_workspace_manager():
    """Mock WorkspaceManager"""
    with patch("src.routers.container.get_workspace_manager") as mock_get:
        mock_manager = MagicMock(spec=WorkspaceManager)
        mock_get.return_value = mock_manager
        yield mock_manager


class TestContainerStartAPI:
    """컨테이너 시작 API 테스트"""
    
    def test_start_container_success(self, client, mock_workspace_manager):
        """컨테이너 시작 성공 테스트"""
        mock_workspace_manager.start_container = AsyncMock(
            return_value=(True, "Container started successfully", "abc123")
        )
        
        response = client.post("/api/workspaces/test-ws/container/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["workspaceId"] == "test-ws"
        assert data["containerId"] == "abc123"
    
    def test_start_container_with_config(self, client, mock_workspace_manager):
        """설정과 함께 컨테이너 시작 테스트"""
        mock_workspace_manager.start_container = AsyncMock(
            return_value=(True, "Container started successfully", "abc123")
        )
        
        # ContainerImage enum 값 사용 (cursor-workspace-python:latest)
        response = client.post(
            "/api/workspaces/test-ws/container/start",
            json={
                "config": {
                    "image": "cursor-workspace-python:latest",
                    "resources": {
                        "cpu_count": 4,
                        "memory_mb": 4096
                    }
                }
            }
        )
        
        assert response.status_code == 200
    
    def test_start_container_failure(self, client, mock_workspace_manager):
        """컨테이너 시작 실패 테스트"""
        mock_workspace_manager.start_container = AsyncMock(
            return_value=(False, "Failed to start container", None)
        )
        
        response = client.post("/api/workspaces/test-ws/container/start")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]


class TestContainerStopAPI:
    """컨테이너 중지 API 테스트"""
    
    def test_stop_container_success(self, client, mock_workspace_manager):
        """컨테이너 중지 성공 테스트"""
        mock_workspace_manager.stop_container = AsyncMock(
            return_value=(True, "Container stopped successfully")
        )
        
        response = client.post("/api/workspaces/test-ws/container/stop")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_stop_container_with_force(self, client, mock_workspace_manager):
        """강제 중지 테스트"""
        mock_workspace_manager.stop_container = AsyncMock(
            return_value=(True, "Container killed")
        )
        
        response = client.post(
            "/api/workspaces/test-ws/container/stop",
            json={"timeout": 5, "force": True}
        )
        
        assert response.status_code == 200


class TestContainerRestartAPI:
    """컨테이너 재시작 API 테스트"""
    
    def test_restart_container_success(self, client, mock_workspace_manager):
        """컨테이너 재시작 성공 테스트"""
        mock_workspace_manager.restart_container = AsyncMock(
            return_value=(True, "Container restarted successfully", "abc123")
        )
        
        response = client.post("/api/workspaces/test-ws/container/restart")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestContainerRemoveAPI:
    """컨테이너 삭제 API 테스트"""
    
    def test_remove_container_success(self, client, mock_workspace_manager):
        """컨테이너 삭제 성공 테스트"""
        mock_workspace_manager.remove_container = AsyncMock(
            return_value=(True, "Container removed successfully")
        )
        
        response = client.delete("/api/workspaces/test-ws/container")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_remove_container_force(self, client, mock_workspace_manager):
        """강제 삭제 테스트"""
        mock_workspace_manager.remove_container = AsyncMock(
            return_value=(True, "Container removed")
        )
        
        response = client.delete("/api/workspaces/test-ws/container?force=true")
        
        assert response.status_code == 200


class TestContainerStatusAPI:
    """컨테이너 상태 조회 API 테스트"""
    
    def test_get_container_status(self, client, mock_workspace_manager):
        """상태 조회 테스트"""
        mock_workspace_manager.get_status = AsyncMock(
            return_value=ContainerStatusResponse(
                workspace_id="test-ws",
                container_id="abc123",
                status=ContainerStatus.RUNNING,
                image="python:3.11-slim",
                cpu_usage_percent=25.5,
                memory_usage_mb=512,
            )
        )
        
        response = client.get("/api/workspaces/test-ws/container/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["workspaceId"] == "test-ws"
        assert data["status"] == "running"
        assert data["cpuUsagePercent"] == 25.5


class TestContainerLogsAPI:
    """컨테이너 로그 조회 API 테스트"""
    
    def test_get_container_logs(self, client, mock_workspace_manager):
        """로그 조회 테스트"""
        mock_workspace_manager.get_logs = AsyncMock(
            return_value=ContainerLogsResponse(
                workspace_id="test-ws",
                logs="2024-01-01T00:00:00 Hello World\n"
            )
        )
        
        response = client.get("/api/workspaces/test-ws/container/logs?tail=50")
        
        assert response.status_code == 200
        data = response.json()
        assert "Hello World" in data["logs"]
    
    def test_get_container_logs_with_time_range(self, client, mock_workspace_manager):
        """시간 범위 로그 조회 테스트"""
        mock_workspace_manager.get_logs = AsyncMock(
            return_value=ContainerLogsResponse(
                workspace_id="test-ws",
                logs="log content",
                since="2024-01-01T00:00:00",
                until="2024-01-02T00:00:00",
            )
        )
        
        response = client.get(
            "/api/workspaces/test-ws/container/logs"
            "?since=2024-01-01T00:00:00Z&until=2024-01-02T00:00:00Z"
        )
        
        assert response.status_code == 200


class TestExecuteCommandAPI:
    """명령 실행 API 테스트"""
    
    def test_execute_command_success(self, client, mock_workspace_manager):
        """명령 실행 성공 테스트"""
        mock_workspace_manager.execute_command = AsyncMock(
            return_value=ExecuteCommandResponse(
                exit_code=0,
                stdout="hello world\n",
                stderr="",
                duration_ms=50,
            )
        )
        
        response = client.post(
            "/api/workspaces/test-ws/execute",
            json={"command": "echo hello world"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["exitCode"] == 0
        assert "hello world" in data["stdout"]
    
    def test_execute_command_with_working_dir(self, client, mock_workspace_manager):
        """작업 디렉토리 지정 명령 실행 테스트"""
        mock_workspace_manager.execute_command = AsyncMock(
            return_value=ExecuteCommandResponse(
                exit_code=0,
                stdout="file.txt\n",
                stderr="",
                duration_ms=30,
            )
        )
        
        response = client.post(
            "/api/workspaces/test-ws/execute",
            json={
                "command": "ls",
                "working_dir": "src",
                "timeout": 30
            }
        )
        
        assert response.status_code == 200
    
    def test_execute_command_container_not_found(self, client, mock_workspace_manager):
        """컨테이너 없을 때 명령 실행 테스트"""
        mock_workspace_manager.execute_command = AsyncMock(
            side_effect=WorkspaceManagerError(
                "Container does not exist",
                code="CONTAINER_NOT_FOUND"
            )
        )
        
        response = client.post(
            "/api/workspaces/test-ws/execute",
            json={"command": "ls"}
        )
        
        assert response.status_code == 404
    
    def test_execute_command_container_not_running(self, client, mock_workspace_manager):
        """컨테이너 중지 상태에서 명령 실행 테스트"""
        mock_workspace_manager.execute_command = AsyncMock(
            side_effect=WorkspaceManagerError(
                "Container is not running",
                code="CONTAINER_NOT_RUNNING"
            )
        )
        
        response = client.post(
            "/api/workspaces/test-ws/execute",
            json={"command": "ls"}
        )
        
        assert response.status_code == 400
    
    def test_execute_command_timeout(self, client, mock_workspace_manager):
        """명령 타임아웃 테스트"""
        mock_workspace_manager.execute_command = AsyncMock(
            side_effect=WorkspaceManagerError(
                "Command execution timed out after 60 seconds",
                code="COMMAND_TIMEOUT"
            )
        )
        
        response = client.post(
            "/api/workspaces/test-ws/execute",
            json={"command": "sleep 100", "timeout": 60}
        )
        
        assert response.status_code == 408
    
    def test_execute_dangerous_command_blocked(self, client):
        """위험한 명령 차단 테스트"""
        # 요청 모델 레벨에서 차단됨
        response = client.post(
            "/api/workspaces/test-ws/execute",
            json={"command": "rm -rf / "}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_execute_command_path_traversal_blocked(self, client):
        """경로 탈출 차단 테스트"""
        response = client.post(
            "/api/workspaces/test-ws/execute",
            json={"command": "ls", "working_dir": "../../../etc"}
        )
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
