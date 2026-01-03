# 기존 프로젝트 + Opus 스캐폴드 통합 설계서

> **버전**: 1.0  
> **작성일**: 2026-01-03  
> **브랜치**: `feature/browser-vscode-webide`

---

## 1. 개요

### 1.1 목적

기존 `cursor-onprem-poc` 프로젝트와 Opus가 설계한 VDE Web IDE 스캐폴드(`docs/claudeaivdedev/`)를 통합하여, **브라우저 기반 VS Code + Cursor 수준 AI 코딩 플랫폼**을 구축합니다.

### 1.2 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **점진적 전환** | 기존 Monaco IDE를 유지하면서 code-server IDE를 병행 도입 |
| **기존 자산 활용** | apps/api, DB, Redis, vLLM 등 기존 인프라 재사용 |
| **모듈화** | 새로운 기능은 독립 서비스로 추가하여 영향 최소화 |
| **Opus 스캐폴드 준수** | 검증된 설정과 구조를 최대한 활용 |

---

## 2. 현재 vs 목표 아키텍처

### 2.1 현재 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 브라우저                            │
└─────────────────────────────┬───────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│  apps/web (Next.js)     │       │  apps/api (FastAPI)     │
│  - Monaco Editor IDE    │◄─────►│  - Workspace API        │
│  - AIChat Component     │       │  - Files API            │
│  - Dashboard            │       │  - AI Router            │
└─────────────────────────┘       └───────────┬─────────────┘
                                              │
                                              ▼
                                  ┌─────────────────────────┐
                                  │  cursor-poc-vllm        │
                                  │  (Qwen2.5-Coder-7B)     │
                                  └─────────────────────────┘
```

### 2.2 목표 아키텍처 (통합 후)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              사용자 브라우저                                   │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ HTTPS
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Nginx Reverse Proxy                                  │
│                    - TLS 종단, 동적 라우팅                                    │
└───────────┬─────────────────────────┬─────────────────────────┬─────────────┘
            │                         │                         │
            ▼                         ▼                         ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌─────────────────────────┐
│    Keycloak           │ │  apps/web (Next.js)   │ │  User IDE Containers    │
│    (SSO/MFA)          │ │  - Dashboard          │ │                         │
│                       │ │  - Workspace Manager  │ │  ┌─────────────────┐    │
│  → 신규 추가          │ │  - (Monaco IDE 유지)  │ │  │ user-1-ws-abc   │    │
└───────────────────────┘ └───────────┬───────────┘ │  │ code-server     │    │
                                      │             │  │ + Tabby Ext     │    │
                                      ▼             │  │ + Continue Ext  │    │
                          ┌───────────────────────┐ │  └─────────────────┘    │
                          │  apps/api (FastAPI)   │ │                         │
                          │  - Workspace API      │ │  ┌─────────────────┐    │
                          │  - Files API          │ │  │ user-2-ws-xyz   │    │
                          │  - AI Gateway API     │ │  │ code-server     │    │
                          │  - IDE Manager API ★  │ │  └─────────────────┘    │
                          └───────────┬───────────┘ └────────────┬────────────┘
                                      │                          │
        ┌─────────────────────────────┼──────────────────────────┤
        │                             │                          │
        ▼                             ▼                          ▼
┌───────────────┐          ┌───────────────────┐      ┌───────────────────┐
│   LiteLLM     │          │   Tabby Server    │      │   cursor-poc-vllm │
│   Proxy       │◄────────►│   (자동완성)       │      │   (Chat/Agent)    │
│   → 신규 추가 │          │   → 신규 추가     │      │   기존 유지       │
└───────────────┘          └───────────────────┘      └───────────────────┘
```

---

## 3. 서비스 매핑

### 3.1 기존 서비스 (유지/확장)

| 서비스 | 현재 역할 | 변경 사항 |
|--------|----------|----------|
| `cursor-poc-postgres` | 사용자/워크스페이스 DB | 유지 |
| `cursor-poc-redis` | 캐시/세션 | 유지 |
| `cursor-poc-api` | REST API 서버 | **IDE Manager API 추가** |
| `cursor-poc-web` | 대시보드/Monaco IDE | **워크스페이스 관리 중심으로 전환** |
| `cursor-poc-vllm` | LLM 추론 | 유지 (Chat/Agent용) |
| `cursor-poc-grafana` | 모니터링 | 유지 |
| `cursor-poc-portainer` | Docker 관리 | 유지 |

### 3.2 신규 서비스 (Opus 스캐폴드 기반)

| 서비스 | 역할 | 이미지 | 포트 |
|--------|------|--------|------|
| `cursor-poc-nginx` | Reverse Proxy | nginx:1.25-alpine | 80, 443 |
| `cursor-poc-keycloak` | SSO/MFA 인증 | keycloak:23.0 | 8080 |
| `cursor-poc-tabby` | AI 자동완성 | tabbyml/tabby:0.21.0 | 8081 |
| `cursor-poc-litellm` | LLM Gateway | litellm:main-latest | 4000 |
| `cursor-poc-ide-{user}-{ws}` | 사용자별 IDE | code-server:4.96.4 | 동적 |

---

## 4. 통합 docker-compose.yml 설계

### 4.1 서비스 그룹

```yaml
# 그룹 1: 기존 핵심 서비스 (유지)
- postgres
- redis
- api
- vllm

# 그룹 2: 신규 인증/프록시 서비스
- nginx        # Reverse Proxy
- keycloak     # SSO/MFA

# 그룹 3: AI 서비스 (신규)
- tabby        # 자동완성 (GPU)
- litellm      # LLM Gateway

# 그룹 4: 동적 IDE 컨테이너 (API에서 생성)
- ide-{user_id}-{workspace_id}  # 사용자별 code-server

# 그룹 5: 관리/모니터링 (유지)
- grafana
- portainer
```

### 4.2 네트워크 구조

```yaml
networks:
  cursor-network:       # 기존 네트워크 (유지)
    driver: bridge
  
  ide-network:          # IDE 컨테이너 전용 (신규)
    driver: bridge
    internal: true      # 외부 접근 차단
```

---

## 5. API 확장 설계

### 5.1 IDE Manager API (신규)

`apps/api/src/routers/ide_manager.py`:

```python
# IDE 컨테이너 관리 API
router = APIRouter(prefix="/api/ide", tags=["IDE Manager"])

@router.post("/provision")
async def provision_ide(workspace_id: str, user_id: str) -> IDEProvisionResponse:
    """사용자별 IDE 컨테이너 프로비저닝"""
    pass

@router.get("/status/{container_id}")
async def get_ide_status(container_id: str) -> IDEStatusResponse:
    """IDE 컨테이너 상태 조회"""
    pass

@router.post("/start/{container_id}")
async def start_ide(container_id: str) -> IDEActionResponse:
    """IDE 컨테이너 시작"""
    pass

@router.post("/stop/{container_id}")
async def stop_ide(container_id: str) -> IDEActionResponse:
    """IDE 컨테이너 중지"""
    pass

@router.delete("/{container_id}")
async def delete_ide(container_id: str) -> IDEActionResponse:
    """IDE 컨테이너 삭제"""
    pass

@router.get("/url/{container_id}")
async def get_ide_url(container_id: str) -> IDEURLResponse:
    """IDE 접속 URL 반환"""
    pass
```

### 5.2 AI Gateway API 확장

`apps/api/src/routers/ai_gateway.py`:

```python
# LiteLLM Proxy 연동 + 정책/감사
router = APIRouter(prefix="/api/ai-gateway", tags=["AI Gateway"])

@router.post("/v1/completions")
async def completions(request: CompletionRequest) -> CompletionResponse:
    """Tabby 호환 자동완성 엔드포인트"""
    # → LiteLLM → Tabby
    pass

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest) -> ChatResponse:
    """Continue 호환 채팅 엔드포인트"""
    # → LiteLLM → vLLM
    pass
```

---

## 6. 프론트엔드 확장 설계

### 6.1 Dashboard 변경

`apps/web/src/app/page.tsx`:

```tsx
// 현재: Monaco IDE 내장
// 변경: 워크스페이스 목록 + IDE 실행 버튼

function WorkspacePage() {
  return (
    <div>
      <WorkspaceList />
      {/* 클릭 시 → code-server IDE로 리다이렉트 */}
    </div>
  );
}
```

### 6.2 IDE 선택 UI

```tsx
// 새로운 컴포넌트: IDE 선택 모달
function WorkspaceActions({ workspaceId }) {
  return (
    <div>
      <Button onClick={() => openCodeServerIDE(workspaceId)}>
        🖥️ VS Code IDE 열기 (권장)
      </Button>
      <Button onClick={() => openMonacoIDE(workspaceId)}>
        📝 간편 편집기 열기
      </Button>
    </div>
  );
}
```

---

## 7. code-server 컨테이너 설계

### 7.1 베이스 이미지 (Dockerfile)

`docker/code-server/Dockerfile`:

```dockerfile
FROM codercom/code-server:4.96.4

# 시스템 패키지
USER root
RUN apt-get update && apt-get install -y \
    git \
    curl \
    python3 \
    python3-pip \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 확장 프로그램 사전 설치
USER coder
RUN code-server --install-extension TabbyML.vscode-tabby \
    && code-server --install-extension Continue.continue \
    && code-server --install-extension ms-python.python \
    && code-server --install-extension dbaeumer.vscode-eslint

# 설정 파일 복사
COPY settings.json /home/coder/.local/share/code-server/User/settings.json
COPY continue-config.json /home/coder/.continue/config.json

# 포트
EXPOSE 8080

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8080/healthz || exit 1

# 시작
ENTRYPOINT ["dumb-init", "code-server", "--bind-addr", "0.0.0.0:8080"]
```

### 7.2 설정 파일

Opus 스캐폴드의 설정 복사:
- `docs/claudeaivdedev/scaffold/configs/code-server/settings.json`
- `docs/claudeaivdedev/scaffold/configs/continue/config.json`

### 7.3 동적 생성 스크립트

`apps/api/src/services/ide_manager.py`:

```python
import docker

class IDEManager:
    def __init__(self):
        self.client = docker.from_env()
    
    def provision_ide(
        self, 
        user_id: str, 
        workspace_id: str,
        workspace_path: str
    ) -> str:
        """IDE 컨테이너 생성"""
        container_name = f"cursor-poc-ide-{user_id}-{workspace_id}"
        
        container = self.client.containers.run(
            image="cursor-poc-code-server:latest",
            name=container_name,
            detach=True,
            environment={
                "PASSWORD": generate_temp_password(),
                "TABBY_ENDPOINT": "http://cursor-poc-tabby:8080",
                "LITELLM_ENDPOINT": "http://cursor-poc-litellm:4000",
            },
            volumes={
                workspace_path: {"bind": "/home/coder/workspace", "mode": "rw"},
            },
            network="cursor-network",
            mem_limit="4g",
            cpu_quota=200000,  # 2 CPU cores
            labels={
                "app": "cursor-ide",
                "user": user_id,
                "workspace": workspace_id,
            },
        )
        
        return container.id
```

---

## 8. 통합 docker-compose.yml (Phase 1)

```yaml
# docker-compose.webide.yml
# 기존 docker-compose.yml과 함께 사용
# docker compose -f docker-compose.yml -f docker-compose.webide.yml up -d

version: '3.8'

services:
  # ===========================================
  # Reverse Proxy (Nginx)
  # ===========================================
  nginx:
    image: nginx:1.25-alpine
    container_name: cursor-poc-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
      - keycloak
    networks:
      - cursor-network
    restart: unless-stopped

  # ===========================================
  # Authentication (Keycloak)
  # ===========================================
  keycloak:
    image: quay.io/keycloak/keycloak:23.0
    container_name: cursor-poc-keycloak
    command: start-dev
    environment:
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:-admin}
      KC_PROXY: edge
      KC_HOSTNAME_STRICT: false
    ports:
      - "8080:8080"
    volumes:
      - keycloak_data:/opt/keycloak/data
    networks:
      - cursor-network
    restart: unless-stopped

  # ===========================================
  # AI Autocomplete (Tabby)
  # ===========================================
  tabby:
    image: tabbyml/tabby:0.21.0
    container_name: cursor-poc-tabby
    command: serve --model StarCoder2-3B --device cuda
    environment:
      TABBY_DISABLE_USAGE_COLLECTION: "1"
    volumes:
      - tabby_data:/data
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "8081:8080"
    networks:
      - cursor-network
    restart: unless-stopped
    profiles:
      - gpu

  # ===========================================
  # LLM Gateway (LiteLLM Proxy)
  # ===========================================
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    container_name: cursor-poc-litellm
    command: --config /app/config.yaml
    environment:
      LITELLM_MASTER_KEY: ${LITELLM_MASTER_KEY:-sk-cursor-poc}
    volumes:
      - ./docker/litellm/config.yaml:/app/config.yaml:ro
    ports:
      - "4000:4000"
    networks:
      - cursor-network
    restart: unless-stopped

volumes:
  keycloak_data:
  tabby_data:
```

---

## 9. 마이그레이션 계획

### Phase 1: 기반 서비스 추가 (1주)

```
□ Nginx Reverse Proxy 추가
□ Keycloak 설치 및 기본 설정
□ LiteLLM Proxy 추가
□ Tabby 서버 추가 (GPU)
□ 네트워크 구성 확인
```

### Phase 2: code-server 이미지 구축 (1주)

```
□ code-server Dockerfile 작성
□ 확장 프로그램 사전 설치
□ 설정 파일 구성
□ 이미지 빌드 및 테스트
```

### Phase 3: API 확장 (1주)

```
□ IDE Manager API 구현
□ AI Gateway API 확장
□ Docker SDK 연동
□ 테스트 작성
```

### Phase 4: 프론트엔드 통합 (1주)

```
□ 워크스페이스 UI 수정
□ IDE 실행 버튼 추가
□ code-server 리다이렉트 구현
□ 통합 테스트
```

---

## 10. 디렉토리 구조 (통합 후)

```
cursor-onprem-poc/
├── apps/
│   ├── api/
│   │   └── src/
│   │       ├── routers/
│   │       │   ├── ai.py              # 기존
│   │       │   ├── ai_gateway.py      # 신규: LiteLLM 연동
│   │       │   ├── files.py           # 기존
│   │       │   ├── ide_manager.py     # 신규: IDE 컨테이너 관리
│   │       │   └── workspaces.py      # 기존
│   │       └── services/
│   │           └── ide_manager.py     # 신규: Docker SDK 연동
│   └── web/
│       └── src/
│           ├── app/
│           │   └── workspace/         # 워크스페이스 페이지 (수정)
│           └── components/
│               ├── AIChat.tsx         # 기존 (유지)
│               ├── CodeEditor.tsx     # 기존 (유지, 간편 편집용)
│               └── IDELauncher.tsx    # 신규: code-server 실행
├── docker/
│   ├── code-server/
│   │   ├── Dockerfile
│   │   ├── settings.json
│   │   └── continue-config.json
│   ├── nginx/
│   │   └── nginx.conf
│   └── litellm/
│       └── config.yaml
├── docker-compose.yml                  # 기존 (유지)
├── docker-compose.webide.yml           # 신규: WebIDE 서비스
└── docs/
    ├── claudeaivdedev/                 # Opus 스캐폴드 (참조)
    └── integration-design.md           # 이 문서
```

---

## 11. 포트 매핑 (통합 후)

| 서비스 | 내부 포트 | 외부 포트 | 비고 |
|--------|----------|----------|------|
| Nginx | 80, 443 | 80, 443 | 메인 진입점 |
| Keycloak | 8080 | 8080 | SSO 관리 |
| API | 8000 | 8000 | REST API |
| Web (Dashboard) | 3000 | 3000 | 대시보드 |
| vLLM | 8000 | 8001 | Chat/Agent |
| Tabby | 8080 | 8081 | 자동완성 |
| LiteLLM | 4000 | 4000 | LLM Gateway |
| code-server (동적) | 8080 | 동적 | 사용자별 IDE |
| Grafana | 3000 | 3001 | 모니터링 |
| Portainer | 9000 | 9000 | Docker 관리 |

---

## 12. 다음 단계

1. **docker-compose.webide.yml 작성** - Phase 1 서비스 정의
2. **docker/code-server/Dockerfile 작성** - IDE 이미지 빌드
3. **IDE Manager API 구현** - 컨테이너 동적 생성
4. **프론트엔드 수정** - IDE 실행 UI
5. **PoC 테스트** - Continue/Tabby 호환성 검증

---

## 13. 참고 문서

- `docs/claudeaivdedev/` - Opus 스캐폴드 전체
- `docs/architecture-comparison.md` - 아키텍처 비교 분석
- `history/2026-01-03_browser-vscode-webide.md` - 변경 이력
