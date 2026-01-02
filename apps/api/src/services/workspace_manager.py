"""
워크스페이스 컨테이너 관리 서비스
Docker SDK를 사용한 컨테이너 라이프사이클 관리

참고:
- Docker SDK Python: https://docker-py.readthedocs.io/en/stable/
- Docker Python API: https://github.com/docker/docker-py
"""

import os
import time
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import docker
from docker.errors import (
    DockerException,
    NotFound,
    APIError,
    ContainerError,
    ImageNotFound,
)
from docker.models.containers import Container
from docker.types import Mount, Resources, LogConfig

from ..models.container import (
    ContainerStatus,
    ContainerImage,
    ContainerConfig,
    ResourceLimits,
    ContainerStatusResponse,
    ContainerLogsResponse,
    ExecuteCommandResponse,
)

logger = logging.getLogger(__name__)


# 기본 워크스페이스 베이스 이미지
DEFAULT_WORKSPACE_IMAGE = os.getenv("WORKSPACE_BASE_IMAGE", "python:3.11-slim")

# 컨테이너 이름 접두사
CONTAINER_PREFIX = "cursor-ws-"

# 워크스페이스 볼륨 기본 경로
WORKSPACES_VOLUME_PATH = os.getenv("WORKSPACES_VOLUME_PATH", "/workspaces")


class WorkspaceManagerError(Exception):
    """워크스페이스 매니저 에러"""
    def __init__(self, message: str, code: str = "WORKSPACE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class WorkspaceManager:
    """
    워크스페이스 컨테이너 관리 서비스
    
    Docker SDK를 사용하여 각 워크스페이스를 독립된 컨테이너로 관리합니다.
    """
    
    _instance: Optional["WorkspaceManager"] = None
    
    def __init__(self):
        """Docker 클라이언트 초기화"""
        try:
            # 환경변수 또는 기본 소켓에서 Docker 클라이언트 생성
            docker_host = os.getenv("DOCKER_HOST")
            if docker_host:
                self.client = docker.DockerClient(base_url=docker_host)
            else:
                self.client = docker.from_env()
            
            # 연결 테스트
            self.client.ping()
            logger.info("Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            # 개발 모드에서는 Mock 모드로 동작
            self.client = None
            logger.warning("Running in mock mode without Docker")
    
    @classmethod
    def get_instance(cls) -> "WorkspaceManager":
        """싱글톤 인스턴스 반환"""
        if cls._instance is None:
            cls._instance = WorkspaceManager()
        return cls._instance
    
    def _get_container_name(self, workspace_id: str) -> str:
        """워크스페이스 ID로 컨테이너 이름 생성"""
        return f"{CONTAINER_PREFIX}{workspace_id}"
    
    def _get_workspace_path(self, workspace_id: str) -> str:
        """워크스페이스 경로 반환"""
        return os.path.join(WORKSPACES_VOLUME_PATH, workspace_id)
    
    def _get_image_name(self, config: Optional[ContainerConfig] = None) -> str:
        """설정에 따른 이미지 이름 반환"""
        if config is None:
            return DEFAULT_WORKSPACE_IMAGE
        
        if config.image == ContainerImage.CUSTOM and config.custom_image:
            return config.custom_image
        
        # 이미지 타입에 따른 기본 이미지 매핑
        image_map = {
            ContainerImage.PYTHON: "python:3.11-slim",
            ContainerImage.NODEJS: "node:20-slim",
            ContainerImage.GOLANG: "golang:1.22-alpine",
            ContainerImage.RUST: "rust:1.76-slim",
            ContainerImage.JAVA: "openjdk:21-slim",
        }
        return image_map.get(config.image, DEFAULT_WORKSPACE_IMAGE)
    
    def _convert_status(self, docker_status: str) -> ContainerStatus:
        """Docker 상태를 ContainerStatus로 변환"""
        status_map = {
            "created": ContainerStatus.CREATING,
            "running": ContainerStatus.RUNNING,
            "paused": ContainerStatus.PAUSED,
            "restarting": ContainerStatus.RESTARTING,
            "removing": ContainerStatus.REMOVING,
            "exited": ContainerStatus.EXITED,
            "dead": ContainerStatus.DEAD,
        }
        return status_map.get(docker_status, ContainerStatus.STOPPED)
    
    def _get_resource_limits(self, limits: ResourceLimits) -> Dict[str, Any]:
        """리소스 제한을 Docker 형식으로 변환"""
        return {
            "nano_cpus": int(limits.cpu_count * 1e9),  # CPU를 나노초 단위로
            "mem_limit": f"{limits.memory_mb}m",  # 메모리 제한
        }
    
    async def get_container(self, workspace_id: str) -> Optional[Container]:
        """워크스페이스 컨테이너 조회"""
        if self.client is None:
            return None
        
        try:
            container_name = self._get_container_name(workspace_id)
            return self.client.containers.get(container_name)
        except NotFound:
            return None
        except APIError as e:
            logger.error(f"Failed to get container for {workspace_id}: {e}")
            return None
    
    async def get_status(self, workspace_id: str) -> ContainerStatusResponse:
        """컨테이너 상태 조회"""
        if self.client is None:
            # Mock 모드
            return ContainerStatusResponse(
                workspace_id=workspace_id,
                container_id=None,
                status=ContainerStatus.STOPPED,
            )
        
        container = await self.get_container(workspace_id)
        
        if container is None:
            return ContainerStatusResponse(
                workspace_id=workspace_id,
                container_id=None,
                status=ContainerStatus.STOPPED,
            )
        
        # 컨테이너 상세 정보 조회
        container.reload()
        attrs = container.attrs
        state = attrs.get("State", {})
        
        # 리소스 사용량 조회
        stats = None
        cpu_percent = None
        memory_mb = None
        
        if state.get("Running"):
            try:
                stats = container.stats(stream=False)
                # CPU 사용률 계산
                cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                           stats["precpu_stats"]["cpu_usage"]["total_usage"]
                system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                              stats["precpu_stats"]["system_cpu_usage"]
                if system_delta > 0:
                    cpu_percent = (cpu_delta / system_delta) * 100
                
                # 메모리 사용량 (MB)
                memory_bytes = stats["memory_stats"].get("usage", 0)
                memory_mb = memory_bytes // (1024 * 1024)
            except Exception as e:
                logger.warning(f"Failed to get container stats: {e}")
        
        return ContainerStatusResponse(
            workspace_id=workspace_id,
            container_id=container.id[:12],
            status=self._convert_status(state.get("Status", "stopped")),
            image=container.image.tags[0] if container.image.tags else None,
            created_at=attrs.get("Created"),
            started_at=state.get("StartedAt"),
            cpu_usage_percent=cpu_percent,
            memory_usage_mb=memory_mb,
        )
    
    async def create_container(
        self,
        workspace_id: str,
        config: Optional[ContainerConfig] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        워크스페이스 컨테이너 생성
        
        Returns:
            Tuple[success, message, container_id]
        """
        if self.client is None:
            # Mock 모드
            return True, "Container created (mock mode)", f"mock-{workspace_id[:8]}"
        
        container_name = self._get_container_name(workspace_id)
        
        # 기존 컨테이너 확인
        existing = await self.get_container(workspace_id)
        if existing:
            return False, "Container already exists", existing.id[:12]
        
        # 설정 준비
        if config is None:
            config = ContainerConfig()
        
        image_name = self._get_image_name(config)
        workspace_path = self._get_workspace_path(workspace_id)
        
        # 워크스페이스 디렉토리 확인/생성
        if not os.path.exists(workspace_path):
            os.makedirs(workspace_path, exist_ok=True)
        
        try:
            # 이미지 풀 (없으면)
            try:
                self.client.images.get(image_name)
            except ImageNotFound:
                logger.info(f"Pulling image: {image_name}")
                self.client.images.pull(image_name)
            
            # 환경 변수 준비
            env = {
                "WORKSPACE_ID": workspace_id,
                "WORKSPACE_PATH": "/workspace",
            }
            if config.env_vars:
                env.update(config.env_vars)
            
            # 컨테이너 생성
            container = self.client.containers.create(
                image=image_name,
                name=container_name,
                hostname=f"ws-{workspace_id[:8]}",
                environment=env,
                working_dir="/workspace",
                # 볼륨 마운트
                mounts=[
                    Mount(
                        target="/workspace",
                        source=workspace_path,
                        type="bind",
                        read_only=False,
                    )
                ],
                # 리소스 제한
                **self._get_resource_limits(config.resources),
                # 네트워크 설정
                network_mode="bridge",
                # 보안 설정
                security_opt=["no-new-privileges:true"],
                # 로그 설정
                log_config=LogConfig(
                    type="json-file",
                    config={"max-size": "10m", "max-file": "3"}
                ),
                # 무한 대기 명령 (컨테이너 유지)
                command=["tail", "-f", "/dev/null"],
                # 자동 재시작 비활성화 (개발 환경)
                restart_policy={"Name": "no"},
                # 라벨
                labels={
                    "cursor.workspace.id": workspace_id,
                    "cursor.managed": "true",
                },
            )
            
            logger.info(f"Container created: {container_name} ({container.id[:12]})")
            return True, "Container created successfully", container.id[:12]
            
        except ImageNotFound as e:
            logger.error(f"Image not found: {image_name}")
            return False, f"Image not found: {image_name}", None
        except APIError as e:
            logger.error(f"Failed to create container: {e}")
            return False, f"Failed to create container: {str(e)}", None
        except Exception as e:
            logger.error(f"Unexpected error creating container: {e}")
            return False, f"Unexpected error: {str(e)}", None
    
    async def start_container(
        self,
        workspace_id: str,
        config: Optional[ContainerConfig] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        워크스페이스 컨테이너 시작
        
        컨테이너가 없으면 새로 생성합니다.
        """
        if self.client is None:
            return True, "Container started (mock mode)", f"mock-{workspace_id[:8]}"
        
        container = await self.get_container(workspace_id)
        
        # 컨테이너가 없으면 생성
        if container is None:
            success, message, container_id = await self.create_container(workspace_id, config)
            if not success:
                return success, message, container_id
            container = await self.get_container(workspace_id)
        
        if container is None:
            return False, "Failed to get container after creation", None
        
        try:
            # 이미 실행 중인지 확인
            container.reload()
            if container.status == "running":
                return True, "Container is already running", container.id[:12]
            
            # 컨테이너 시작
            container.start()
            logger.info(f"Container started: {workspace_id}")
            return True, "Container started successfully", container.id[:12]
            
        except APIError as e:
            logger.error(f"Failed to start container: {e}")
            return False, f"Failed to start container: {str(e)}", None
    
    async def stop_container(
        self,
        workspace_id: str,
        timeout: int = 10,
        force: bool = False
    ) -> Tuple[bool, str]:
        """워크스페이스 컨테이너 중지"""
        if self.client is None:
            return True, "Container stopped (mock mode)"
        
        container = await self.get_container(workspace_id)
        if container is None:
            return True, "Container does not exist"
        
        try:
            container.reload()
            if container.status != "running":
                return True, "Container is not running"
            
            if force:
                container.kill()
                logger.info(f"Container killed: {workspace_id}")
            else:
                container.stop(timeout=timeout)
                logger.info(f"Container stopped: {workspace_id}")
            
            return True, "Container stopped successfully"
            
        except APIError as e:
            logger.error(f"Failed to stop container: {e}")
            return False, f"Failed to stop container: {str(e)}"
    
    async def restart_container(
        self,
        workspace_id: str,
        timeout: int = 10
    ) -> Tuple[bool, str, Optional[str]]:
        """워크스페이스 컨테이너 재시작"""
        if self.client is None:
            return True, "Container restarted (mock mode)", f"mock-{workspace_id[:8]}"
        
        container = await self.get_container(workspace_id)
        if container is None:
            return False, "Container does not exist", None
        
        try:
            container.restart(timeout=timeout)
            logger.info(f"Container restarted: {workspace_id}")
            return True, "Container restarted successfully", container.id[:12]
            
        except APIError as e:
            logger.error(f"Failed to restart container: {e}")
            return False, f"Failed to restart container: {str(e)}", None
    
    async def remove_container(
        self,
        workspace_id: str,
        force: bool = False,
        remove_volumes: bool = False
    ) -> Tuple[bool, str]:
        """워크스페이스 컨테이너 삭제"""
        if self.client is None:
            return True, "Container removed (mock mode)"
        
        container = await self.get_container(workspace_id)
        if container is None:
            return True, "Container does not exist"
        
        try:
            container.remove(force=force, v=remove_volumes)
            logger.info(f"Container removed: {workspace_id}")
            return True, "Container removed successfully"
            
        except APIError as e:
            logger.error(f"Failed to remove container: {e}")
            return False, f"Failed to remove container: {str(e)}"
    
    async def execute_command(
        self,
        workspace_id: str,
        command: str,
        working_dir: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 60
    ) -> ExecuteCommandResponse:
        """
        컨테이너 내에서 명령 실행
        
        참고: docker exec와 동일한 동작
        """
        if self.client is None:
            # Mock 모드
            return ExecuteCommandResponse(
                exit_code=0,
                stdout=f"Mock execution: {command}",
                stderr="",
                duration_ms=10,
            )
        
        container = await self.get_container(workspace_id)
        if container is None:
            raise WorkspaceManagerError(
                "Container does not exist",
                code="CONTAINER_NOT_FOUND"
            )
        
        # 컨테이너가 실행 중인지 확인
        container.reload()
        if container.status != "running":
            raise WorkspaceManagerError(
                "Container is not running",
                code="CONTAINER_NOT_RUNNING"
            )
        
        try:
            start_time = time.time()
            
            # 명령 실행 (exec_run)
            exec_kwargs = {
                "cmd": ["sh", "-c", command],
                "stdout": True,
                "stderr": True,
                "demux": True,  # stdout, stderr 분리
            }
            
            if working_dir:
                exec_kwargs["workdir"] = f"/workspace/{working_dir}"
            
            if env:
                exec_kwargs["environment"] = env
            
            # 비동기 실행을 위한 래핑
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: container.exec_run(**exec_kwargs)),
                timeout=timeout
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            stdout_output = ""
            stderr_output = ""
            
            if result.output:
                if isinstance(result.output, tuple):
                    stdout_output = result.output[0].decode("utf-8") if result.output[0] else ""
                    stderr_output = result.output[1].decode("utf-8") if result.output[1] else ""
                else:
                    stdout_output = result.output.decode("utf-8") if result.output else ""
            
            return ExecuteCommandResponse(
                exit_code=result.exit_code,
                stdout=stdout_output,
                stderr=stderr_output,
                duration_ms=duration_ms,
            )
            
        except asyncio.TimeoutError:
            raise WorkspaceManagerError(
                f"Command execution timed out after {timeout} seconds",
                code="COMMAND_TIMEOUT"
            )
        except APIError as e:
            logger.error(f"Failed to execute command: {e}")
            raise WorkspaceManagerError(
                f"Failed to execute command: {str(e)}",
                code="COMMAND_FAILED"
            )
    
    async def get_logs(
        self,
        workspace_id: str,
        tail: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> ContainerLogsResponse:
        """컨테이너 로그 조회"""
        if self.client is None:
            return ContainerLogsResponse(
                workspace_id=workspace_id,
                logs="No logs available (mock mode)",
            )
        
        container = await self.get_container(workspace_id)
        if container is None:
            return ContainerLogsResponse(
                workspace_id=workspace_id,
                logs="Container does not exist",
            )
        
        try:
            logs_kwargs = {
                "stdout": True,
                "stderr": True,
                "tail": tail,
                "timestamps": True,
            }
            
            if since:
                logs_kwargs["since"] = since
            if until:
                logs_kwargs["until"] = until
            
            logs = container.logs(**logs_kwargs)
            logs_str = logs.decode("utf-8") if isinstance(logs, bytes) else str(logs)
            
            return ContainerLogsResponse(
                workspace_id=workspace_id,
                logs=logs_str,
                since=since.isoformat() if since else None,
                until=until.isoformat() if until else None,
            )
            
        except APIError as e:
            logger.error(f"Failed to get logs: {e}")
            return ContainerLogsResponse(
                workspace_id=workspace_id,
                logs=f"Failed to get logs: {str(e)}",
            )
    
    async def list_containers(
        self,
        status: Optional[ContainerStatus] = None,
        limit: int = 100
    ) -> list:
        """관리 중인 워크스페이스 컨테이너 목록"""
        if self.client is None:
            return []
        
        try:
            filters = {
                "label": "cursor.managed=true"
            }
            
            if status:
                if status in [ContainerStatus.RUNNING, ContainerStatus.PAUSED]:
                    filters["status"] = status.value
                elif status == ContainerStatus.STOPPED:
                    filters["status"] = "exited"
            
            containers = self.client.containers.list(
                all=True,
                filters=filters,
                limit=limit,
            )
            
            result = []
            for container in containers:
                workspace_id = container.labels.get("cursor.workspace.id", container.name)
                workspace_id = workspace_id.replace(CONTAINER_PREFIX, "")
                
                result.append({
                    "workspace_id": workspace_id,
                    "container_id": container.id[:12],
                    "name": container.name,
                    "status": self._convert_status(container.status),
                    "image": container.image.tags[0] if container.image.tags else None,
                })
            
            return result
            
        except APIError as e:
            logger.error(f"Failed to list containers: {e}")
            return []


# 전역 인스턴스 생성 함수
def get_workspace_manager() -> WorkspaceManager:
    """WorkspaceManager 싱글톤 인스턴스 반환"""
    return WorkspaceManager.get_instance()
