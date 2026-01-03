"""
WorkspaceManager 서비스 테스트

이 테스트는 Mock 모드에서 동작합니다.
실제 Docker 환경에서는 Docker가 설치되어 있어야 합니다.

사용법:
    cd apps/api
    pytest tests/test_workspace_manager.py -v
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import os
import sys

# 테스트 환경 설정
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from src.services.workspace_manager import (
    WorkspaceManager,
    WorkspaceManagerError,
    get_workspace_manager,
    CONTAINER_PREFIX,
)
from src.models.container import (
    ContainerStatus,
    ContainerImage,
    ContainerConfig,
    ResourceLimits,
    ExecuteCommandRequest,
)


class TestWorkspaceManagerMock:
    """Mock 모드 테스트 (Docker 없이)"""
    
    @pytest.fixture
    def manager(self):
        """Mock 모드 WorkspaceManager 인스턴스"""
        # 싱글톤 초기화
        WorkspaceManager._instance = None
        
        # 직접 client를 None으로 설정하여 Mock 모드 시뮬레이션
        manager = WorkspaceManager.__new__(WorkspaceManager)
        manager.client = None
        yield manager
    
    @pytest.mark.asyncio
    async def test_get_status_mock_mode(self, manager):
        """Mock 모드에서 상태 조회 테스트"""
        status = await manager.get_status("test-workspace")
        
        assert status.workspace_id == "test-workspace"
        assert status.container_id is None
        assert status.status == ContainerStatus.STOPPED
    
    @pytest.mark.asyncio
    async def test_start_container_mock_mode(self, manager):
        """Mock 모드에서 컨테이너 시작 테스트"""
        success, message, container_id = await manager.start_container("test-workspace")
        
        assert success is True
        assert "mock mode" in message.lower()
        assert container_id.startswith("mock-")
    
    @pytest.mark.asyncio
    async def test_stop_container_mock_mode(self, manager):
        """Mock 모드에서 컨테이너 중지 테스트"""
        success, message = await manager.stop_container("test-workspace")
        
        assert success is True
        assert "mock mode" in message.lower()
    
    @pytest.mark.asyncio
    async def test_restart_container_mock_mode(self, manager):
        """Mock 모드에서 컨테이너 재시작 테스트"""
        success, message, container_id = await manager.restart_container("test-workspace")
        
        assert success is True
        assert "mock mode" in message.lower()
    
    @pytest.mark.asyncio
    async def test_remove_container_mock_mode(self, manager):
        """Mock 모드에서 컨테이너 삭제 테스트"""
        success, message = await manager.remove_container("test-workspace")
        
        assert success is True
        assert "mock mode" in message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_command_mock_mode(self, manager):
        """Mock 모드에서 명령 실행 테스트"""
        result = await manager.execute_command(
            workspace_id="test-workspace",
            command="echo hello",
        )
        
        assert result.exit_code == 0
        assert "Mock execution" in result.stdout
        assert result.stderr == ""
    
    @pytest.mark.asyncio
    async def test_list_containers_mock_mode(self, manager):
        """Mock 모드에서 컨테이너 목록 테스트"""
        containers = await manager.list_containers()
        
        assert containers == []


class TestWorkspaceManagerWithDocker:
    """Docker 연동 테스트 (Mock Docker Client 사용)"""
    
    @pytest.fixture
    def mock_docker_client(self):
        """Mock Docker 클라이언트"""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        return mock_client
    
    @pytest.fixture
    def manager_with_docker(self, mock_docker_client):
        """Docker 클라이언트가 있는 WorkspaceManager"""
        WorkspaceManager._instance = None
        
        with patch("src.services.workspace_manager.docker") as mock_docker:
            mock_docker.from_env.return_value = mock_docker_client
            
            manager = WorkspaceManager()
            assert manager.client is not None
            yield manager
    
    def test_container_name_generation(self, manager_with_docker):
        """컨테이너 이름 생성 테스트"""
        name = manager_with_docker._get_container_name("test-workspace")
        
        assert name == f"{CONTAINER_PREFIX}test-workspace"
    
    def test_image_name_default(self, manager_with_docker):
        """기본 이미지 이름 테스트"""
        image = manager_with_docker._get_image_name(None)
        
        assert "python" in image.lower()
    
    def test_image_name_with_config(self, manager_with_docker):
        """설정에 따른 이미지 이름 테스트"""
        config = ContainerConfig(image=ContainerImage.NODEJS)
        image = manager_with_docker._get_image_name(config)
        
        assert "node" in image.lower()
    
    def test_image_name_custom(self, manager_with_docker):
        """커스텀 이미지 테스트"""
        config = ContainerConfig(
            image=ContainerImage.CUSTOM,
            custom_image="my-custom-image:latest"
        )
        image = manager_with_docker._get_image_name(config)
        
        assert image == "my-custom-image:latest"
    
    def test_status_conversion(self, manager_with_docker):
        """Docker 상태 변환 테스트"""
        assert manager_with_docker._convert_status("running") == ContainerStatus.RUNNING
        assert manager_with_docker._convert_status("exited") == ContainerStatus.EXITED
        assert manager_with_docker._convert_status("paused") == ContainerStatus.PAUSED
        assert manager_with_docker._convert_status("unknown") == ContainerStatus.STOPPED
    
    def test_resource_limits_conversion(self, manager_with_docker):
        """리소스 제한 변환 테스트"""
        limits = ResourceLimits(cpu_count=2.0, memory_mb=1024)
        result = manager_with_docker._get_resource_limits(limits)
        
        assert result["nano_cpus"] == 2000000000  # 2 cores in nanoseconds
        assert result["mem_limit"] == "1024m"
    
    @pytest.mark.asyncio
    async def test_get_container_not_found(self, manager_with_docker):
        """존재하지 않는 컨테이너 조회 테스트"""
        from docker.errors import NotFound
        
        manager_with_docker.client.containers.get.side_effect = NotFound("Not found")
        
        container = await manager_with_docker.get_container("nonexistent")
        
        assert container is None
    
    @pytest.mark.asyncio
    async def test_get_status_with_container(self, manager_with_docker):
        """컨테이너가 있을 때 상태 조회 테스트"""
        mock_container = MagicMock()
        mock_container.id = "abc123456789"
        mock_container.status = "running"
        mock_container.attrs = {
            "State": {"Status": "running", "StartedAt": "2024-01-01T00:00:00Z"},
            "Created": "2024-01-01T00:00:00Z",
        }
        mock_container.image.tags = ["python:3.11-slim"]
        mock_container.stats.return_value = {
            "cpu_stats": {
                "cpu_usage": {"total_usage": 1000000000},
                "system_cpu_usage": 100000000000,
            },
            "precpu_stats": {
                "cpu_usage": {"total_usage": 900000000},
                "system_cpu_usage": 99000000000,
            },
            "memory_stats": {"usage": 104857600},  # 100MB
        }
        
        manager_with_docker.client.containers.get.return_value = mock_container
        
        status = await manager_with_docker.get_status("test-workspace")
        
        assert status.workspace_id == "test-workspace"
        assert status.container_id == "abc123456789"[:12]
        assert status.status == ContainerStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_create_container_already_exists(self, manager_with_docker):
        """컨테이너가 이미 존재할 때 생성 테스트"""
        mock_container = MagicMock()
        mock_container.id = "existing123"
        
        manager_with_docker.client.containers.get.return_value = mock_container
        
        success, message, container_id = await manager_with_docker.create_container(
            "test-workspace"
        )
        
        assert success is False
        assert "already exists" in message.lower()


class TestContainerModels:
    """컨테이너 모델 테스트"""
    
    def test_resource_limits_defaults(self):
        """리소스 제한 기본값 테스트"""
        limits = ResourceLimits()
        
        assert limits.cpu_count == 2.0
        assert limits.memory_mb == 2048
        assert limits.disk_mb == 10240
    
    def test_resource_limits_validation(self):
        """리소스 제한 유효성 검사 테스트"""
        # 최소값 테스트
        limits = ResourceLimits(cpu_count=0.5, memory_mb=256)
        assert limits.cpu_count == 0.5
        
        # 최대값 테스트
        limits = ResourceLimits(cpu_count=16, memory_mb=32768)
        assert limits.cpu_count == 16
        
        # 범위 초과 테스트
        with pytest.raises(ValueError):
            ResourceLimits(cpu_count=0.1)  # 최소 0.5
        
        with pytest.raises(ValueError):
            ResourceLimits(memory_mb=100)  # 최소 256
    
    def test_container_config_custom_image_validation(self):
        """커스텀 이미지 유효성 검사 테스트"""
        from pydantic import ValidationError
        
        # 커스텀 이미지 없이 CUSTOM 선택 시 에러
        with pytest.raises(ValidationError):
            ContainerConfig(image=ContainerImage.CUSTOM)
        
        # 올바른 커스텀 이미지
        config = ContainerConfig(
            image=ContainerImage.CUSTOM,
            custom_image="my-image:latest"
        )
        assert config.custom_image == "my-image:latest"
    
    def test_execute_command_request_validation(self):
        """명령 실행 요청 유효성 검사 테스트"""
        # 정상 명령
        req = ExecuteCommandRequest(command="ls -la")
        assert req.command == "ls -la"
        
        # 위험한 명령 차단
        with pytest.raises(ValueError):
            ExecuteCommandRequest(command="rm -rf / ")
        
        # 경로 탈출 차단
        with pytest.raises(ValueError):
            ExecuteCommandRequest(command="ls", working_dir="../../../etc")


class TestSingleton:
    """싱글톤 패턴 테스트"""
    
    def test_get_workspace_manager_singleton(self):
        """싱글톤 인스턴스 테스트"""
        # 기존 인스턴스 사용 (Docker 연결 상태와 관계없이)
        manager1 = get_workspace_manager()
        manager2 = get_workspace_manager()
        
        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
