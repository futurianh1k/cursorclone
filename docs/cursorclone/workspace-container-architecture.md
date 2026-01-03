# 워크스페이스 컨테이너 아키텍처 설계

**작성일**: 2025-01-02  
**상태**: 설계 단계  
**목적**: GitHub Codespace, Google Colab, Replit과 유사한 격리된 워크스페이스 환경 제공

---

## 1. 문제점 분석

### 현재 구현의 한계

1. **격리 부족**
   - 모든 워크스페이스가 같은 호스트 파일시스템 공유
   - 워크스페이스 간 파일 접근 가능 (보안 취약)
   - 리소스 제한 없음 (CPU, 메모리, 디스크)

2. **실행 환경 부재**
   - 코드 실행 기능 없음
   - 의존성 관리 불가능
   - 터미널/쉘 접근 불가

3. **확장성 문제**
   - 동시 워크스페이스 수 제한 없음
   - 리소스 관리 불가능
   - 멀티 테넌트 지원 어려움

4. **보안 취약점**
   - 파일시스템 기반 경로 검증만으로는 부족
   - 코드 실행 시 호스트 시스템 노출 위험
   - 네트워크 격리 없음

---

## 2. 목표 아키텍처

### 2.1 컨테이너 기반 워크스페이스

각 워크스페이스는 독립적인 Docker 컨테이너로 실행됩니다.

```
┌─────────────────────────────────────────────────────────┐
│                    API 서버 (FastAPI)                    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         워크스페이스 관리자 (Workspace Manager)  │  │
│  │  - 컨테이너 생성/삭제/관리                        │  │
│  │  - 리소스 모니터링                                │  │
│  │  - 라이프사이클 관리                              │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Docker API
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Container   │ │  Container   │ │  Container   │
│  ws_001      │ │  ws_002      │ │  ws_003      │
│              │ │              │ │              │
│  /workspace  │ │  /workspace  │ │  /workspace  │
│  - code      │ │  - code      │ │  - code      │
│  - .git      │ │  - .git      │ │  - .git      │
│  - deps      │ │  - deps      │ │  - deps      │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 2.2 워크스페이스 라이프사이클

```
생성 요청
    ↓
컨테이너 생성 (Docker)
    ↓
볼륨 마운트 (/workspaces/ws_xxx)
    ↓
초기 설정 (Git clone, 의존성 설치)
    ↓
실행 중 (Active)
    ↓
비활성화 (일정 시간 후 자동 정지)
    ↓
삭제 (사용자 요청 또는 정책에 따라)
```

---

## 3. 구현 방안

### 3.1 Docker 기반 구현 (MVP)

**장점**:
- 구현 간단
- 빠른 프로토타이핑
- 개발 환경과 유사

**단점**:
- 단일 호스트 제한
- 수동 스케일링
- 고가용성 어려움

**구현 예시**:

```python
# apps/api/src/services/workspace_manager.py

import docker
from pathlib import Path
from typing import Optional
import asyncio

class WorkspaceManager:
    """워크스페이스 컨테이너 관리자"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.base_image = "python:3.11-slim"  # 또는 커스텀 이미지
        self.workspace_base = Path("/workspaces")
    
    async def create_workspace_container(
        self,
        workspace_id: str,
        source: Optional[str] = None,  # GitHub URL 또는 None
    ) -> str:
        """워크스페이스 컨테이너 생성"""
        
        workspace_path = self.workspace_base / workspace_id
        
        # 볼륨 마운트 설정
        volumes = {
            str(workspace_path): {
                "bind": "/workspace",
                "mode": "rw"
            }
        }
        
        # 컨테이너 생성
        container = self.client.containers.create(
            image=self.base_image,
            name=f"ws_{workspace_id}",
            volumes=volumes,
            working_dir="/workspace",
            command="tail -f /dev/null",  # 계속 실행 유지
            detach=True,
            network_disabled=False,  # 필요시 네트워크 격리
            mem_limit="2g",  # 메모리 제한
            cpu_period=100000,
            cpu_quota=50000,  # CPU 50% 제한
            security_opt=["no-new-privileges"],  # 권한 상승 방지
            read_only=False,  # /workspace는 쓰기 가능
        )
        
        # 컨테이너 시작
        container.start()
        
        # 초기 설정 (Git clone 등)
        if source:
            await self._setup_workspace(container, source)
        
        return container.id
    
    async def _setup_workspace(self, container, source: str):
        """워크스페이스 초기 설정"""
        # Git clone 실행
        exec_result = container.exec_run(
            f"git clone {source} /workspace",
            user="root"
        )
        
        if exec_result.exit_code != 0:
            raise RuntimeError(f"Failed to clone: {exec_result.output.decode()}")
    
    async def stop_workspace(self, workspace_id: str):
        """워크스페이스 컨테이너 정지"""
        container_name = f"ws_{workspace_id}"
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=10)
        except docker.errors.NotFound:
            pass
    
    async def remove_workspace(self, workspace_id: str):
        """워크스페이스 컨테이너 삭제"""
        container_name = f"ws_{workspace_id}"
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=True)
        except docker.errors.NotFound:
            pass
    
    async def execute_command(
        self,
        workspace_id: str,
        command: str,
        timeout: int = 30,
    ) -> dict:
        """워크스페이스 내 명령 실행"""
        container_name = f"ws_{workspace_id}"
        container = self.client.containers.get(container_name)
        
        exec_result = container.exec_run(
            command,
            user="workspace",  # 비특권 사용자
            timeout=timeout,
        )
        
        return {
            "exit_code": exec_result.exit_code,
            "output": exec_result.output.decode(),
        }
```

### 3.2 Kubernetes 기반 구현 (프로덕션)

**장점**:
- 자동 스케일링
- 고가용성
- 리소스 관리 우수
- 멀티 노드 지원

**단점**:
- 복잡도 높음
- 인프라 요구사항 높음

**구현 예시**:

```yaml
# Kubernetes Pod 템플릿

apiVersion: v1
kind: Pod
metadata:
  name: ws-{workspace_id}
  labels:
    workspace-id: {workspace_id}
spec:
  containers:
  - name: workspace
    image: python:3.11-slim
    workingDir: /workspace
    volumeMounts:
    - name: workspace-storage
      mountPath: /workspace
    resources:
      requests:
        memory: "512Mi"
        cpu: "0.5"
      limits:
        memory: "2Gi"
        cpu: "2"
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: false
  volumes:
  - name: workspace-storage
    persistentVolumeClaim:
      claimName: ws-{workspace_id}-pvc
```

---

## 4. 보안 고려사항

### 4.1 컨테이너 격리

1. **네트워크 격리**
   - 각 워크스페이스는 독립적인 네트워크 네임스페이스
   - 외부 네트워크 접근 제한 (온프레미스 요구사항)
   - 필요한 경우 내부 서비스만 접근 허용

2. **파일시스템 격리**
   - 컨테이너 내부 파일시스템만 접근 가능
   - 호스트 파일시스템 접근 불가
   - 볼륨 마운트는 `/workspace`만 허용

3. **리소스 제한**
   - CPU, 메모리, 디스크 할당량 제한
   - 프로세스 수 제한
   - 네트워크 대역폭 제한

### 4.2 권한 관리

```python
# 컨테이너 보안 설정
security_opt = [
    "no-new-privileges",  # 권한 상승 방지
    "seccomp=unconfined",  # 필요시 조정
]

# 비특권 사용자로 실행
user = "workspace:workspace"  # UID:GID
```

---

## 5. API 변경사항

### 5.1 워크스페이스 생성 API

```python
@router.post("/api/workspaces")
async def create_workspace(request: CreateWorkspaceRequest):
    """
    워크스페이스 생성 시 컨테이너도 함께 생성
    """
    workspace_id = f"ws_{request.name}"
    
    # 1. 디렉토리 생성
    workspace_root = get_workspace_root(workspace_id)
    workspace_root.mkdir(parents=True, exist_ok=False)
    
    # 2. 컨테이너 생성
    workspace_manager = WorkspaceManager()
    container_id = await workspace_manager.create_workspace_container(
        workspace_id=workspace_id,
        source=None,  # 빈 워크스페이스
    )
    
    # 3. 메타데이터 저장 (DB)
    # ...
    
    return WorkspaceResponse(
        workspaceId=workspace_id,
        name=request.name,
        rootPath=str(workspace_root),
        containerId=container_id,  # 새 필드
        status="running",  # 새 필드
    )
```

### 5.2 GitHub 클론 API

```python
@router.post("/api/workspaces/clone")
async def clone_github_repository(request: CloneGitHubRequest):
    """
    GitHub 클론 시 컨테이너 내부에서 실행
    """
    workspace_id = f"ws_{workspace_name}"
    
    # 1. 디렉토리 생성
    workspace_root = get_workspace_root(workspace_id)
    workspace_root.mkdir(parents=True, exist_ok=False)
    
    # 2. 컨테이너 생성 및 Git clone
    workspace_manager = WorkspaceManager()
    container_id = await workspace_manager.create_workspace_container(
        workspace_id=workspace_id,
        source=request.repository_url,  # Git clone 실행
    )
    
    return WorkspaceResponse(...)
```

### 5.3 명령 실행 API (새로 추가)

```python
@router.post("/api/workspaces/{ws_id}/execute")
async def execute_command(
    ws_id: str,
    request: ExecuteCommandRequest,
):
    """
    워크스페이스 컨테이너 내 명령 실행
    예: pip install, npm install, python script.py 등
    """
    workspace_manager = WorkspaceManager()
    result = await workspace_manager.execute_command(
        workspace_id=ws_id,
        command=request.command,
        timeout=request.timeout or 30,
    )
    
    return ExecuteCommandResponse(
        exit_code=result["exit_code"],
        output=result["output"],
    )
```

---

## 6. 구현 단계

### Phase 1: MVP (현재)
- [x] 파일시스템 기반 워크스페이스
- [x] GitHub 클론 기능
- [ ] 기본 보안 검증

### Phase 2: Docker 통합
- [ ] WorkspaceManager 구현
- [ ] 컨테이너 생성/삭제 API
- [ ] 명령 실행 API
- [ ] 리소스 모니터링

### Phase 3: 고급 기능
- [ ] 자동 비활성화 (일정 시간 후 정지)
- [ ] 컨테이너 재시작
- [ ] 로그 수집
- [ ] 리소스 사용량 통계

### Phase 4: 프로덕션 준비
- [ ] Kubernetes 마이그레이션
- [ ] 자동 스케일링
- [ ] 고가용성 구성
- [ ] 백업/복구

---

## 7. 참고 자료

- **Docker SDK**: https://docker-py.readthedocs.io/
- **Kubernetes Python Client**: https://github.com/kubernetes-client/python
- **GitHub Codespace Architecture**: https://github.blog/2021-08-11-githubs-engineering-team-moved-3-1-million-files-from-ipfs-to-blob-storage/
- **Google Colab Architecture**: https://research.google.com/colaboratory/faq.html

---

## 8. 다음 단계

1. **WorkspaceManager 서비스 구현**
   - Docker SDK 통합
   - 컨테이너 라이프사이클 관리
   - 명령 실행 기능

2. **API 엔드포인트 확장**
   - 컨테이너 상태 조회
   - 명령 실행 API
   - 로그 조회 API

3. **보안 강화**
   - 네트워크 격리
   - 리소스 제한
   - 권한 관리

4. **모니터링 및 로깅**
   - 컨테이너 상태 모니터링
   - 리소스 사용량 추적
   - 감사 로그
