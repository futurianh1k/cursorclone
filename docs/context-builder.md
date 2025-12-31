# Context Builder 설계 문서

**작성일**: 2025-12-31  
**버전**: 0.1.0 (PoC)  
**상태**: Draft

---

## 1. 개요

### 1.1 목적

Context Builder는 **API 레이어와 LLM 사이의 중간 계층**으로, LLM에 전달할 컨텍스트를 조합하고 최적화하는 역할을 담당합니다.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Web IDE   │ ──▶ │   API Gateway    │ ──▶ │    vLLM     │
│  (Next.js)  │     │    (FastAPI)     │     │  (On-Prem)  │
└─────────────┘     └────────┬─────────┘     └─────────────┘
                             │
                    ┌────────▼─────────┐
                    │  Context Builder │  ◀── 이 문서의 대상
                    │                  │
                    │ - 컨텍스트 조합   │
                    │ - 프롬프트 생성   │
                    │ - 토큰 최적화     │
                    └──────────────────┘
```

### 1.2 설계 원칙

1. **API는 LLM을 직접 호출하지 않는다** - 반드시 Context Builder 경유
2. **프롬프트/응답 원문 로깅 금지** - hash + 메타데이터만 저장
3. **보안 우선** - 민감 정보 필터링, 경로 검증
4. **확장 가능** - 새로운 컨텍스트 소스 추가 용이

---

## 2. 아키텍처

### 2.1 전체 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                        Context Builder                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │  Context    │   │  Prompt     │   │   Token     │           │
│  │  Collector  │──▶│  Assembler  │──▶│  Optimizer  │──▶ LLM    │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│        │                 │                                      │
│        ▼                 ▼                                      │
│  ┌─────────────┐   ┌─────────────┐                             │
│  │  Security   │   │  Template   │                             │
│  │  Filter     │   │  Registry   │                             │
│  └─────────────┘   └─────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 컴포넌트 설명

| 컴포넌트 | 역할 | 상태 |
|----------|------|------|
| **Context Collector** | 여러 소스에서 컨텍스트 수집 | PoC 대상 |
| **Security Filter** | 민감 정보 필터링, 경로 검증 | PoC 대상 |
| **Template Registry** | 프롬프트 템플릿 관리 | PoC 대상 |
| **Prompt Assembler** | 최종 프롬프트 조합 | PoC 대상 |
| **Token Optimizer** | 토큰 제한 내 최적화 | PoC 후 |

---

## 3. 컨텍스트 소스

### 3.1 PoC 범위 (MVP)

| 소스 | 설명 | 우선순위 |
|------|------|----------|
| **Selection** | 사용자가 선택한 코드 범위 | P0 |
| **Current File** | 현재 편집 중인 파일 전체 | P0 |
| **User Instruction** | 사용자 지시사항 | P0 |

### 3.2 확장 예정 (Post-PoC)

| 소스 | 설명 | 우선순위 |
|------|------|----------|
| **Related Files** | import/include 관계 파일 | P1 |
| **Repo Index** | 전체 코드베이스 검색 결과 | P2 |
| **Git History** | 최근 변경 이력 | P2 |
| **Documentation** | 프로젝트 문서 | P3 |

---

## 4. 인터페이스 설계

### 4.1 Context Builder 입력 (Request)

```python
from pydantic import BaseModel
from typing import Optional, List

class SelectionRange(BaseModel):
    start_line: int
    end_line: int
    start_col: Optional[int] = None
    end_col: Optional[int] = None

class ContextSource(BaseModel):
    """컨텍스트 소스 정의"""
    type: str  # "selection" | "file" | "related" | "search"
    path: str
    content: Optional[str] = None
    range: Optional[SelectionRange] = None

class ContextBuildRequest(BaseModel):
    """Context Builder 요청"""
    workspace_id: str
    action: str  # "rewrite" | "explain" | "generate" | "chat"
    instruction: str
    sources: List[ContextSource]
    
    # 선택적 옵션
    max_tokens: Optional[int] = 4096
    include_related: Optional[bool] = False
```

### 4.2 Context Builder 출력 (Response)

```python
class PromptMessage(BaseModel):
    """LLM 메시지 형식"""
    role: str  # "system" | "user" | "assistant"
    content: str

class ContextBuildResponse(BaseModel):
    """Context Builder 응답"""
    messages: List[PromptMessage]
    
    # 메타데이터 (로깅용)
    metadata: dict  # {
                    #   "action": "rewrite",
                    #   "source_count": 2,
                    #   "total_tokens_estimate": 1500,
                    #   "context_hash": "sha256:abc123..."
                    # }
```

### 4.3 Python 인터페이스

```python
# apps/api/src/context_builder/builder.py

from abc import ABC, abstractmethod

class ContextBuilder(ABC):
    """Context Builder 추상 클래스"""
    
    @abstractmethod
    async def build(self, request: ContextBuildRequest) -> ContextBuildResponse:
        """컨텍스트를 조합하여 LLM 프롬프트 생성"""
        pass

class DefaultContextBuilder(ContextBuilder):
    """기본 Context Builder 구현"""
    
    def __init__(
        self,
        template_registry: TemplateRegistry,
        security_filter: SecurityFilter,
    ):
        self.templates = template_registry
        self.security = security_filter
    
    async def build(self, request: ContextBuildRequest) -> ContextBuildResponse:
        # 1. 보안 필터링
        validated_sources = await self.security.validate(request.sources)
        
        # 2. 컨텍스트 수집
        context = await self._collect_context(validated_sources)
        
        # 3. 프롬프트 조합
        messages = await self._assemble_prompt(
            action=request.action,
            instruction=request.instruction,
            context=context
        )
        
        # 4. 메타데이터 생성 (원문 저장 금지)
        metadata = self._create_metadata(request, messages)
        
        return ContextBuildResponse(messages=messages, metadata=metadata)
```

---

## 5. 프롬프트 템플릿 시스템

### 5.1 템플릿 구조

```
packages/prompt-templates/
├── README.md
├── system/           # 시스템 프롬프트
│   ├── base.md       # 공통 기본 규칙
│   ├── rewrite.md    # 코드 리라이트용
│   └── explain.md    # 코드 설명용
└── user/             # 유저 프롬프트 템플릿
    ├── rewrite.md
    └── explain.md
```

### 5.2 현재 템플릿 (rewrite.md)

```markdown
SYSTEM:
You are a code refactoring assistant for an enterprise on-prem environment.
You MUST output only a unified diff. No extra text.

RULES:
- Do not output full files
- Do not change unrelated code
- Preserve formatting
- If unsure, output an empty diff
```

### 5.3 템플릿 변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `{{instruction}}` | 사용자 지시사항 | "이 함수를 async로 변경해줘" |
| `{{selection}}` | 선택된 코드 | `def foo(): ...` |
| `{{file_path}}` | 파일 경로 | `src/utils.py` |
| `{{file_content}}` | 전체 파일 내용 | (전체 코드) |
| `{{language}}` | 프로그래밍 언어 | `python` |

### 5.4 조합 예시

**입력:**
```python
request = ContextBuildRequest(
    workspace_id="ws_demo",
    action="rewrite",
    instruction="이 함수를 async로 변경해줘",
    sources=[
        ContextSource(
            type="selection",
            path="src/api.py",
            content="def fetch_data():\n    return requests.get(url)",
            range=SelectionRange(start_line=10, end_line=12)
        )
    ]
)
```

**출력 (messages):**
```python
[
    {
        "role": "system",
        "content": "You are a code refactoring assistant for an enterprise on-prem environment.\nYou MUST output only a unified diff. No extra text.\n\nRULES:\n- Do not output full files\n- Do not change unrelated code\n- Preserve formatting\n- If unsure, output an empty diff"
    },
    {
        "role": "user", 
        "content": "File: src/api.py (lines 10-12)\n\n```python\ndef fetch_data():\n    return requests.get(url)\n```\n\nInstruction: 이 함수를 async로 변경해줘"
    }
]
```

---

## 6. 보안 필터

### 6.1 검증 항목

| 항목 | 검증 내용 | 실패 시 |
|------|----------|---------|
| **경로 검증** | `../` 등 경로 탈출 시도 | 400 Bad Request |
| **Workspace 격리** | 다른 workspace 접근 시도 | 403 Forbidden |
| **파일 크기** | 단일 파일 최대 크기 초과 | 413 Payload Too Large |
| **총 컨텍스트 크기** | 총 토큰 제한 초과 | 자동 truncate |
| **확장자 검증** | 허용되지 않은 파일 형식 | 400 Bad Request |

### 6.2 허용 파일 확장자 (Allowlist)

```python
ALLOWED_EXTENSIONS = {
    # 프로그래밍 언어
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".c", ".cpp", ".h",
    ".rb", ".php", ".swift", ".kt",
    
    # 설정/마크업
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".txt", ".html", ".css", ".scss",
    
    # 기타
    ".sql", ".sh", ".bash", ".dockerfile",
}
```

### 6.3 Security Filter 인터페이스

```python
class SecurityFilter:
    """보안 필터"""
    
    def __init__(self, workspace_root: str, config: SecurityConfig):
        self.workspace_root = workspace_root
        self.config = config
    
    async def validate(self, sources: List[ContextSource]) -> List[ContextSource]:
        """컨텍스트 소스 보안 검증"""
        validated = []
        for source in sources:
            # 1. 경로 정규화 및 검증
            if not self._validate_path(source.path):
                raise SecurityError(f"Invalid path: {source.path}")
            
            # 2. 확장자 검증
            if not self._validate_extension(source.path):
                raise SecurityError(f"Disallowed extension: {source.path}")
            
            # 3. 크기 검증
            if source.content and len(source.content) > self.config.max_file_size:
                source.content = self._truncate(source.content)
            
            validated.append(source)
        
        return validated
    
    def _validate_path(self, path: str) -> bool:
        """경로 탈출 방지"""
        normalized = os.path.normpath(path)
        
        # 절대 경로 금지
        if os.path.isabs(normalized):
            return False
        
        # 상위 디렉토리 이동 금지
        if normalized.startswith(".."):
            return False
        
        # 심볼릭 링크 검증
        full_path = os.path.join(self.workspace_root, normalized)
        real_path = os.path.realpath(full_path)
        if not real_path.startswith(self.workspace_root):
            return False
        
        return True
```

---

## 7. 감사 로그

### 7.1 로깅 원칙

> **원문 저장 금지**: 프롬프트/응답 원문은 저장하지 않고, hash + 메타데이터만 저장

### 7.2 로그 스키마

```python
class ContextBuildAuditLog(BaseModel):
    """Context Builder 감사 로그"""
    
    # 식별자
    log_id: str  # UUID
    timestamp: datetime
    
    # 사용자/워크스페이스
    user_id: str
    workspace_id: str
    
    # 요청 메타데이터
    action: str  # "rewrite" | "explain" | "chat"
    source_count: int
    source_paths: List[str]  # 파일 경로만 (내용 X)
    
    # 해시 (검증용)
    instruction_hash: str  # SHA-256
    context_hash: str      # SHA-256
    response_hash: str     # SHA-256 (LLM 응답)
    
    # 성능 메트릭
    tokens_estimated: int
    latency_ms: int
```

### 7.3 로그 예시

```json
{
  "log_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-31T14:30:00Z",
  "user_id": "u_demo",
  "workspace_id": "ws_demo",
  "action": "rewrite",
  "source_count": 1,
  "source_paths": ["src/api.py"],
  "instruction_hash": "sha256:a1b2c3d4...",
  "context_hash": "sha256:e5f6g7h8...",
  "response_hash": "sha256:i9j0k1l2...",
  "tokens_estimated": 1500,
  "latency_ms": 2340
}
```

---

## 8. 구현 계획

### 8.1 디렉토리 구조

```
apps/api/src/
├── main.py
├── context_builder/
│   ├── __init__.py
│   ├── builder.py        # ContextBuilder 클래스
│   ├── collector.py      # ContextCollector
│   ├── security.py       # SecurityFilter
│   ├── templates.py      # TemplateRegistry
│   └── models.py         # Pydantic 모델
└── routers/
    └── ai.py             # /ai/* 라우터
```

### 8.2 구현 단계

| 단계 | 내용 | 의존성 | 예상 기간 |
|------|------|--------|----------|
| 1 | 모델 정의 (models.py) | - | 0.5일 |
| 2 | Security Filter | Task C (Diff 유틸) | 1일 |
| 3 | Template Registry | prompt-templates | 0.5일 |
| 4 | Context Collector (기본) | - | 1일 |
| 5 | Prompt Assembler | 2, 3 | 1일 |
| 6 | API 라우터 연동 | Task B (API 명세) | 0.5일 |
| 7 | 테스트 작성 | 전체 | 1일 |

**총 예상 기간**: 5.5일

### 8.3 의존성

```
Task C (Diff 유틸) ─────┐
                        ├──▶ Context Builder ──▶ Task D (LLM Router)
Task B (API 명세) ──────┘
```

---

## 9. 테스트 계획

### 9.1 단위 테스트

```python
# tests/test_context_builder.py

import pytest
from context_builder import DefaultContextBuilder, SecurityFilter

class TestSecurityFilter:
    """보안 필터 테스트"""
    
    def test_path_traversal_blocked(self):
        """경로 탈출 시도 차단"""
        filter = SecurityFilter("/workspaces/ws_demo", config)
        
        with pytest.raises(SecurityError):
            filter.validate([
                ContextSource(type="file", path="../../../etc/passwd")
            ])
    
    def test_symlink_escape_blocked(self):
        """심볼릭 링크 탈출 차단"""
        # ...
    
    def test_valid_path_allowed(self):
        """정상 경로 허용"""
        # ...

class TestContextBuilder:
    """Context Builder 테스트"""
    
    def test_rewrite_prompt_format(self):
        """rewrite 프롬프트 형식 검증"""
        # ...
    
    def test_metadata_no_content(self):
        """메타데이터에 원문 미포함 검증"""
        # ...
```

### 9.2 통합 테스트

```python
class TestContextBuilderIntegration:
    """통합 테스트"""
    
    async def test_full_flow(self):
        """전체 흐름: API → Context Builder → (mock) LLM"""
        # ...
```

---

## 10. 향후 확장

### 10.1 Token Optimizer (Post-PoC)

토큰 제한 내에서 컨텍스트를 최적화하는 기능:

- 중요도 기반 컨텍스트 우선순위
- 코드 압축 (주석 제거, 공백 최적화)
- 청크 분할 및 요약

### 10.2 Repo Index 연동 (Post-PoC)

전체 코드베이스 검색을 위한 인덱스 연동:

- 시맨틱 검색 (임베딩 기반)
- 키워드 검색
- 심볼 검색 (함수/클래스 정의)

### 10.3 Streaming 지원

LLM 응답 스트리밍을 위한 확장:

```python
async def build_stream(
    self, 
    request: ContextBuildRequest
) -> AsyncGenerator[PromptMessage, None]:
    """스트리밍 컨텍스트 빌드"""
    # ...
```

---

## 부록 A. 설정 파일

```python
# config/context_builder.py

from pydantic import BaseSettings

class ContextBuilderConfig(BaseSettings):
    """Context Builder 설정"""
    
    # 크기 제한
    max_file_size: int = 100_000  # 100KB
    max_total_context: int = 500_000  # 500KB
    max_tokens: int = 8192
    
    # 보안
    allowed_extensions: set = ALLOWED_EXTENSIONS
    enable_symlink_check: bool = True
    
    # 템플릿
    template_dir: str = "packages/prompt-templates"
    
    class Config:
        env_prefix = "CTX_"
```

---

## 부록 B. 에러 코드

| 코드 | 이름 | 설명 |
|------|------|------|
| `CTX_001` | PATH_TRAVERSAL | 경로 탈출 시도 |
| `CTX_002` | WORKSPACE_VIOLATION | 워크스페이스 격리 위반 |
| `CTX_003` | EXTENSION_DENIED | 허용되지 않은 확장자 |
| `CTX_004` | SIZE_EXCEEDED | 크기 제한 초과 |
| `CTX_005` | TEMPLATE_NOT_FOUND | 템플릿 없음 |
| `CTX_006` | INVALID_ACTION | 지원하지 않는 action |

---

## 참고 자료

- **프로젝트 아키텍처**: `docs/architecture.md`
- **API 명세**: `docs/api-spec.md`
- **AGENTS 규칙**: `AGENTS.md`
- **프롬프트 템플릿**: `packages/prompt-templates/`
- **온프레미스 Runbook**: `docs/runbook-onprem.md`
