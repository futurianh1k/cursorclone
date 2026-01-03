"""
IDE 컨테이너 API 테스트
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.main import app

client = TestClient(app)


class TestIDEContainerAPI:
    """IDE 컨테이너 API 테스트 클래스"""

    def test_create_ide_container(self):
        """IDE 컨테이너 생성 테스트"""
        response = client.post(
            "/api/ide/containers",
            json={
                "workspaceId": "test-workspace-123",
                "ideType": "code-server",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "containerId" in data
        assert data["workspaceId"] == "test-workspace-123"
        assert data["ideType"] == "code-server"
        assert data["status"] in ["pending", "starting", "running"]

    def test_create_ide_container_with_config(self):
        """설정을 포함한 IDE 컨테이너 생성 테스트"""
        response = client.post(
            "/api/ide/containers",
            json={
                "workspaceId": "test-workspace-456",
                "ideType": "code-server",
                "config": {
                    "cpuLimit": "4",
                    "memoryLimit": "8Gi",
                    "storageSize": "20Gi",
                },
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["config"] is not None

    def test_list_ide_containers(self):
        """IDE 컨테이너 목록 조회 테스트"""
        response = client.get("/api/ide/containers")
        
        assert response.status_code == 200
        data = response.json()
        assert "containers" in data
        assert "total" in data
        assert isinstance(data["containers"], list)

    def test_list_ide_containers_with_filter(self):
        """워크스페이스 ID로 필터링된 IDE 컨테이너 목록 조회 테스트"""
        # 먼저 컨테이너 생성
        client.post(
            "/api/ide/containers",
            json={"workspaceId": "filter-test-ws"},
        )
        
        response = client.get("/api/ide/containers?workspace_id=filter-test-ws")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["containers"], list)
        # 필터링된 결과만 반환되어야 함
        for container in data["containers"]:
            assert container["workspaceId"] == "filter-test-ws"

    def test_get_ide_container_not_found(self):
        """존재하지 않는 IDE 컨테이너 조회 테스트"""
        response = client.get("/api/ide/containers/non-existent-id")
        
        assert response.status_code == 404

    def test_ide_health(self):
        """IDE 서비스 상태 조회 테스트"""
        response = client.get("/api/ide/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "totalContainers" in data
        assert "runningContainers" in data
        assert "availableCapacity" in data

    def test_get_workspace_ide_url(self):
        """워크스페이스 IDE URL 조회 테스트"""
        response = client.get("/api/ide/workspace/test-workspace/url")
        
        assert response.status_code == 200
        data = response.json()
        assert "url" in data
        assert "status" in data

    def test_stop_ide_container_not_found(self):
        """존재하지 않는 IDE 컨테이너 중지 테스트"""
        response = client.post("/api/ide/containers/non-existent-id/stop")
        
        assert response.status_code == 404

    def test_delete_ide_container_not_found(self):
        """존재하지 않는 IDE 컨테이너 삭제 테스트"""
        response = client.delete("/api/ide/containers/non-existent-id")
        
        assert response.status_code == 404


class TestIDEContainerLifecycle:
    """IDE 컨테이너 라이프사이클 테스트"""

    def test_full_lifecycle(self):
        """전체 라이프사이클 테스트: 생성 → 조회 → 중지 → 삭제"""
        # 1. 생성
        create_response = client.post(
            "/api/ide/containers",
            json={"workspaceId": "lifecycle-test"},
        )
        assert create_response.status_code == 200
        container_id = create_response.json()["containerId"]
        
        # 2. 조회
        get_response = client.get(f"/api/ide/containers/{container_id}")
        assert get_response.status_code == 200
        assert get_response.json()["containerId"] == container_id
        
        # 3. 중지
        stop_response = client.post(f"/api/ide/containers/{container_id}/stop")
        assert stop_response.status_code == 200
        assert stop_response.json()["status"] in ["stopped", "stopping"]
        
        # 4. 삭제
        delete_response = client.delete(f"/api/ide/containers/{container_id}")
        assert delete_response.status_code == 200
        
        # 5. 삭제 후 조회 시 404
        get_after_delete = client.get(f"/api/ide/containers/{container_id}")
        assert get_after_delete.status_code == 404


class TestIDEContainerValidation:
    """IDE 컨테이너 요청 검증 테스트"""

    def test_create_without_workspace_id(self):
        """워크스페이스 ID 없이 생성 시도 테스트"""
        response = client.post(
            "/api/ide/containers",
            json={"ideType": "code-server"},
        )
        
        # Pydantic 검증 실패로 422 반환
        assert response.status_code == 422

    def test_create_with_invalid_ide_type(self):
        """잘못된 IDE 타입으로 생성 시도 테스트"""
        response = client.post(
            "/api/ide/containers",
            json={
                "workspaceId": "test",
                "ideType": "invalid-type",
            },
        )
        
        # Pydantic 검증 실패로 422 반환
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
