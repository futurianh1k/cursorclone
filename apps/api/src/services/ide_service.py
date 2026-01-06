"""
IDE 컨테이너 관리 서비스
워크스페이스 생성 시 VSCode Server 자동 프로비저닝

참조:
- code-server: https://github.com/coder/code-server
- Docker SDK: https://docker-py.readthedocs.io/
"""

import os
import uuid
import logging
import asyncio
from typing import Optional, Tuple
from datetime import datetime, timezone

# Docker SDK
try:
    import docker
    from docker.errors import DockerException, NotFound, ImageNotFound
    DOCKER_AVAILABLE = True
except ImportError:
    docker = None
    DOCKER_AVAILABLE = False

logger = logging.getLogger(__name__)


# ============================================================
# 설정
# ============================================================

# 커스텀 code-server 이미지 (Tabby + Continue 확장 포함)
IDE_CONTAINER_IMAGE = os.getenv("IDE_CONTAINER_IMAGE", "cursor-poc-code-server:latest")
IDE_NETWORK = os.getenv("IDE_NETWORK", "cursor-network")
IDE_PORT_RANGE_START = int(os.getenv("IDE_PORT_RANGE_START", "9100"))
IDE_PORT_RANGE_END = int(os.getenv("IDE_PORT_RANGE_END", "9200"))
IDE_BASE_URL = os.getenv("IDE_BASE_URL", "http://localhost")
WORKSPACE_BASE_PATH = os.getenv("WORKSPACE_BASE_PATH", "/workspaces")


# In-memory 저장소 (PoC용)
_ide_containers: dict[str, dict] = {}
_used_ports: set[int] = set()


class IDEService:
    """IDE 컨테이너 관리 서비스 (싱글톤)"""
    
    _instance: Optional["IDEService"] = None
    
    def __init__(self):
        self.client = None
        if DOCKER_AVAILABLE:
            try:
                docker_host = os.getenv("DOCKER_HOST")
                if docker_host:
                    self.client = docker.DockerClient(base_url=docker_host)
                else:
                    self.client = docker.from_env()
                self.client.ping()
                logger.info("IDE Service: Docker client initialized")
            except Exception as e:
                logger.warning(f"IDE Service: Docker not available: {e}")
                self.client = None
    
    @classmethod
    def get_instance(cls) -> "IDEService":
        if cls._instance is None:
            cls._instance = IDEService()
        return cls._instance
    
    def _allocate_port(self) -> int:
        """사용 가능한 포트 할당"""
        for port in range(IDE_PORT_RANGE_START, IDE_PORT_RANGE_END):
            if port not in _used_ports:
                _used_ports.add(port)
                return port
        raise RuntimeError("사용 가능한 포트가 없습니다")
    
    def _release_port(self, port: int):
        """포트 해제"""
        _used_ports.discard(port)
    
    async def create_ide_container(
        self,
        workspace_id: str,
        user_id: str,
        memory_limit: str = "2g",
        cpu_limit: str = "2",
    ) -> Tuple[bool, str, Optional[str], Optional[int]]:
        """
        워크스페이스용 IDE 컨테이너 생성
        
        Args:
            workspace_id: 워크스페이스 ID
            user_id: 사용자 ID
            memory_limit: 메모리 제한
            cpu_limit: CPU 제한
            
        Returns:
            (success, message, ide_url, port)
        """
        # 컨테이너 이름: ide-{workspace_id} 형식으로 직관적으로 생성
        container_id = f"ide-{workspace_id}"
        
        # 기존 컨테이너 확인
        existing = self.get_container_for_workspace(workspace_id, user_id)
        if existing:
            return True, "기존 IDE 컨테이너 사용", existing.get("url"), existing.get("port")
        
        try:
            port = self._allocate_port()
        except RuntimeError as e:
            return False, str(e), None, None
        
        # 컨테이너 정보 저장
        now = datetime.now(timezone.utc).isoformat()
        container_info = {
            "container_id": container_id,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "status": "pending",
            "url": None,
            "port": port,
            "created_at": now,
        }
        _ide_containers[container_id] = container_info
        
        # 비동기 컨테이너 생성
        asyncio.create_task(self._create_container_async(
            container_id, workspace_id, port, memory_limit, cpu_limit
        ))
        
        return True, f"IDE 컨테이너 생성 시작: {container_id}", f"{IDE_BASE_URL}:{port}", port
    
    async def _create_container_async(
        self,
        container_id: str,
        workspace_id: str,
        port: int,
        memory_limit: str,
        cpu_limit: str,
    ):
        """비동기 컨테이너 생성"""
        try:
            _ide_containers[container_id]["status"] = "starting"
            
            if self.client:
                # 워크스페이스 경로 (호스트 경로)
                host_workspace_path = os.path.join(
                    os.getenv("HOST_WORKSPACE_PATH", "/home/ubuntu/projects/cursor-onprem-poc/workspaces"),
                    workspace_id
                )
                
                # 이미지 확인/풀
                try:
                    self.client.images.get(IDE_CONTAINER_IMAGE)
                except ImageNotFound:
                    logger.info(f"Pulling IDE image: {IDE_CONTAINER_IMAGE}")
                    self.client.images.pull(IDE_CONTAINER_IMAGE)
                
                # code-server 컨테이너 생성
                # --auth none 으로 비밀번호 없이 접근 가능하도록 설정
                # Tabby 및 vLLM 서버 주소 환경변수로 전달
                tabby_endpoint = os.getenv("TABBY_ENDPOINT", "http://cursor-poc-tabby:8080")
                vllm_endpoint = os.getenv("VLLM_ENDPOINT", "http://cursor-poc-vllm:8000/v1")
                
                container = self.client.containers.run(
                    IDE_CONTAINER_IMAGE,
                    command=["--auth", "none", "--bind-addr", "0.0.0.0:8080"],
                    detach=True,
                    name=container_id,
                    ports={"8080/tcp": port},
                    volumes={
                        host_workspace_path: {"bind": "/home/coder/project", "mode": "rw"}
                    },
                    environment={
                        "WORKSPACE_ID": workspace_id,
                        "TABBY_API_ENDPOINT": tabby_endpoint,
                        "VLLM_API_ENDPOINT": vllm_endpoint,
                    },
                    network=IDE_NETWORK,
                    mem_limit=memory_limit,
                    cpu_period=100000,
                    cpu_quota=int(float(cpu_limit) * 100000),
                    labels={
                        "cursor.workspace_id": workspace_id,
                        "cursor.container_id": container_id,
                        "cursor.type": "ide",
                    },
                )
                
                # 시작 대기 (최대 30초)
                for _ in range(30):
                    container.reload()
                    if container.status == "running":
                        break
                    await asyncio.sleep(1)
                
                ide_url = f"{IDE_BASE_URL}:{port}"
                _ide_containers[container_id]["status"] = "running"
                _ide_containers[container_id]["url"] = ide_url
                
                logger.info(f"IDE 컨테이너 생성 완료: {container_id}, URL: {ide_url}")
            else:
                # Docker 없는 경우 (Mock)
                await asyncio.sleep(2)
                ide_url = f"{IDE_BASE_URL}:{port}"
                _ide_containers[container_id]["status"] = "running"
                _ide_containers[container_id]["url"] = ide_url
                
                logger.info(f"IDE 컨테이너 (Mock) 생성: {container_id}")
                
        except Exception as e:
            logger.error(f"IDE 컨테이너 생성 실패: {container_id}, error: {e}")
            _ide_containers[container_id]["status"] = "error"
            self._release_port(port)
    
    def get_container_for_workspace(
        self,
        workspace_id: str,
        user_id: str,
    ) -> Optional[dict]:
        """워크스페이스의 IDE 컨테이너 조회"""
        for container in _ide_containers.values():
            if (container["workspace_id"] == workspace_id 
                and container["user_id"] == user_id
                and container["status"] not in ["stopped", "error"]):
                return container
        return None
    
    def get_all_containers(self) -> dict:
        """모든 IDE 컨테이너 조회"""
        return _ide_containers.copy()
    
    async def stop_container(self, container_id: str, remove: bool = False) -> Tuple[bool, str]:
        """
        IDE 컨테이너 정지
        
        Args:
            container_id: 컨테이너 ID
            remove: True면 컨테이너 삭제, False면 중지만 (상태 보존)
        """
        if container_id not in _ide_containers:
            return False, "컨테이너를 찾을 수 없습니다"
        
        try:
            if self.client:
                try:
                    container = self.client.containers.get(container_id)
                    container.stop(timeout=10)
                    if remove:
                        container.remove()
                except NotFound:
                    pass
            
            # remove=True인 경우에만 포트 해제
            if remove:
                port = _ide_containers[container_id].get("port")
                if port:
                    self._release_port(port)
                del _ide_containers[container_id]
                logger.info(f"IDE 컨테이너 삭제: {container_id}")
                return True, "컨테이너가 삭제되었습니다"
            else:
                _ide_containers[container_id]["status"] = "stopped"
                logger.info(f"IDE 컨테이너 정지 (상태 보존): {container_id}")
                return True, "컨테이너가 정지되었습니다. 다시 시작하면 이전 상태가 복원됩니다."
            
        except Exception as e:
            logger.error(f"IDE 컨테이너 정지 실패: {container_id}, error: {e}")
            return False, str(e)
    
    async def start_container(self, container_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        중지된 IDE 컨테이너 재시작 (상태 복원)
        
        Returns:
            (success, message, url)
        """
        if container_id not in _ide_containers:
            return False, "컨테이너를 찾을 수 없습니다", None
        
        container_info = _ide_containers[container_id]
        
        if container_info["status"] == "running":
            return True, "컨테이너가 이미 실행 중입니다", container_info.get("url")
        
        try:
            if self.client:
                try:
                    container = self.client.containers.get(container_id)
                    container.start()
                    
                    # 시작 대기 (최대 30초)
                    for _ in range(30):
                        container.reload()
                        if container.status == "running":
                            break
                        await asyncio.sleep(1)
                    
                    container_info["status"] = "running"
                    url = f"{IDE_BASE_URL}:{container_info['port']}"
                    container_info["url"] = url
                    logger.info(f"IDE 컨테이너 재시작: {container_id}")
                    return True, "컨테이너가 시작되었습니다", url
                    
                except NotFound:
                    # 컨테이너가 삭제된 경우 새로 생성
                    logger.warning(f"컨테이너 {container_id}가 없음, 새로 생성")
                    del _ide_containers[container_id]
                    return False, "컨테이너가 존재하지 않습니다. 새로 생성해주세요.", None
            else:
                # Mock 모드
                container_info["status"] = "running"
                url = f"{IDE_BASE_URL}:{container_info['port']}"
                container_info["url"] = url
                return True, "컨테이너가 시작되었습니다 (Mock)", url
                
        except Exception as e:
            logger.error(f"IDE 컨테이너 시작 실패: {container_id}, error: {e}")
            return False, str(e), None
    
    async def delete_container(self, container_id: str) -> Tuple[bool, str]:
        """IDE 컨테이너 완전 삭제"""
        return await self.stop_container(container_id, remove=True)


# 싱글톤 인스턴스 접근
def get_ide_service() -> IDEService:
    return IDEService.get_instance()
