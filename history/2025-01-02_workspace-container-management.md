# 워크스페이스 컨테이너 관리 기능 구현

**작성일**: 2025-01-02  
**브랜치**: `feature/workspace-container-management`  
**작성자**: AI Assistant (Claude)

---

## 1. 요청자 요구사항 요약

사용자가 요청한 내용:
> 워크스페이스 컨테이너 관리 구현
> 현재는 파일시스템 기반이며, 실제 Docker/Kubernetes 컨테이너로 격리 실행이 필요합니다.
> 작업 내용:
> - WorkspaceManager 서비스 구현 (Docker SDK 통합)
> - 컨테이너 생성/삭제/재시작 API
> - 리소스 제한 설정 (CPU, Memory)
> - 컨테이너 내 명령 실행 API (/api/workspaces/{id}/execute)

---

## 2. Assistant 응답 내용

워크스페이스별로 독립된 Docker 컨테이너를 생성하고 관리하는 기능을 구현합니다.

### 주요 구현 내용

1. **Docker SDK 통합**
   - `docker` Python 패키지 사용
   - 환경에 Docker가 없으면 Mock 모드로 동작

2. **WorkspaceManager 서비스**
   - 싱글톤 패턴으로 구현
   - 컨테이너 라이프사이클 관리 (생성/시작/중지/재시작/삭제)
   - 리소스 제한 설정 (CPU, Memory)
   - 명령 실행 기능

3. **컨테이너 API 엔드포인트**
   - `POST /api/workspaces/{id}/container/start`
   - `POST /api/workspaces/{id}/container/stop`
   - `POST /api/workspaces/{id}/container/restart`
   - `DELETE /api/workspaces/{id}/container`
   - `GET /api/workspaces/{id}/container/status`
   - `GET /api/workspaces/{id}/container/logs`
   - `POST /api/workspaces/{id}/execute`

4. **보안 기능**
   - 위험한 명령 패턴 차단
   - 경로 탈출 방지
   - 리소스 제한 강제

---

## 3. 실제로 수행한 변경 내용

### 파일 생성/수정 요약

| 파일 경로 | 변경 유형 | 설명 |
|-----------|-----------|------|
| `apps/api/requirements.txt` | 수정 | docker, websockets 패키지 추가 |
| `apps/api/src/models/container.py` | 생성 | 컨테이너 관련 Pydantic 모델 |
| `apps/api/src/models/__init__.py` | 생성 | 모델 패키지 초기화 |
| `apps/api/src/services/workspace_manager.py` | 생성 | WorkspaceManager 서비스 |
| `apps/api/src/services/__init__.py` | 수정 | WorkspaceManager 추가 |
| `apps/api/src/routers/container.py` | 생성 | 컨테이너 API 라우터 |
| `apps/api/src/routers/__init__.py` | 수정 | container_router 추가 |
| `apps/api/src/main.py` | 수정 | 컨테이너 라우터 등록 |
| `apps/api/tests/test_workspace_manager.py` | 생성 | WorkspaceManager 테스트 |
| `apps/api/tests/test_container_api.py` | 생성 | API 엔드포인트 테스트 |

### 주요 코드 설명

#### 컨테이너 모델 (`models/container.py`)

```python
class ContainerStatus(str, Enum):
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    # ...

class ResourceLimits(BaseModel):
    cpu_count: float = Field(default=2.0, ge=0.5, le=16)
    memory_mb: int = Field(default=2048, ge=256, le=32768)
    disk_mb: int = Field(default=10240, ge=1024, le=102400)

class ExecuteCommandRequest(BaseModel):
    command: str
    working_dir: Optional[str] = None
    env: Optional[dict] = None
    timeout: int = Field(default=60, ge=1, le=3600)
```

#### WorkspaceManager 서비스 (`services/workspace_manager.py`)

```python
class WorkspaceManager:
    """워크스페이스 컨테이너 관리 서비스"""
    
    async def start_container(self, workspace_id, config=None):
        """컨테이너 시작 (없으면 생성)"""
        
    async def stop_container(self, workspace_id, timeout=10, force=False):
        """컨테이너 중지"""
        
    async def execute_command(self, workspace_id, command, ...):
        """컨테이너 내 명령 실행"""
```

#### 컨테이너 API (`routers/container.py`)

```python
@router.post("/{workspace_id}/container/start")
async def start_container(workspace_id: str, request: StartContainerRequest):
    """컨테이너 시작"""

@router.post("/{workspace_id}/execute")
async def execute_command(workspace_id: str, request: ExecuteCommandRequest):
    """명령 실행"""
```

---

## 4. 테스트 및 검증 방법

### 단위 테스트 실행

```bash
cd apps/api
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Mock 모드 테스트
pytest tests/test_workspace_manager.py -v

# API 테스트
pytest tests/test_container_api.py -v
```

### 실제 Docker 환경 테스트

```bash
# Docker가 설치된 환경에서
docker compose up -d api

# API 호출 테스트
curl -X POST http://localhost:8000/api/workspaces/test-ws/container/start
curl -X GET http://localhost:8000/api/workspaces/test-ws/container/status
curl -X POST http://localhost:8000/api/workspaces/test-ws/execute \
  -H "Content-Type: application/json" \
  -d '{"command": "ls -la"}'
```

### 테스트 커버리지

- WorkspaceManager 서비스 테스트: Mock 모드, Docker 연동
- API 엔드포인트 테스트: 성공/실패 케이스
- 모델 유효성 검사 테스트: 리소스 제한, 위험 명령 차단

---

## 5. 향후 작업 제안

### 즉시 필요

1. **Kubernetes 연동**
   - 현재는 Docker만 지원
   - Kubernetes Deployment/Pod 관리 추가 필요

2. **WebSocket 실시간 터미널**
   - 현재는 단일 명령 실행만 지원
   - 대화형 터미널 세션 필요

3. **리소스 모니터링 강화**
   - Prometheus 메트릭 수집
   - 실시간 리소스 사용량 알림

### 중기 계획

4. **이미지 관리**
   - 커스텀 이미지 빌드 기능
   - 이미지 캐싱 및 배포

5. **네트워크 격리**
   - 워크스페이스별 네트워크 분리
   - 보안 그룹 설정

6. **데이터 영속성**
   - 컨테이너 상태 DB 저장
   - 자동 복구 기능

---

## 6. 참고 자료

- **Docker SDK Python**: https://docker-py.readthedocs.io/en/stable/
- **Docker Python API**: https://github.com/docker/docker-py
- **FastAPI 의존성 주입**: https://fastapi.tiangolo.com/tutorial/dependencies/

---

## 7. 관련 커밋 메시지 제안

```
feat(container): 워크스페이스 컨테이너 관리 기능 구현

요청 내용:
- 워크스페이스를 Docker 컨테이너로 격리 실행
- 컨테이너 생성/삭제/재시작 API
- 리소스 제한 설정 (CPU, Memory)
- 컨테이너 내 명령 실행 API

구현 내용:
- WorkspaceManager 서비스 (Docker SDK 통합)
- 컨테이너 관련 Pydantic 모델
- 컨테이너 API 라우터 (/api/workspaces/{id}/container/*)
- 명령 실행 API (/api/workspaces/{id}/execute)
- 단위 테스트 및 API 테스트

수정 파일:
- apps/api/requirements.txt (docker, websockets 추가)
- apps/api/src/models/container.py (신규)
- apps/api/src/services/workspace_manager.py (신규)
- apps/api/src/routers/container.py (신규)
- apps/api/tests/test_*.py (테스트)
```
