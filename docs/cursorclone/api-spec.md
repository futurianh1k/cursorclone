# API Spec (MVP)

**버전**: 0.1.0  
**상태**: Task B 완료 (스켈레톤 구현)  
**기준일**: 2025-12-31

---

## 개요

사내 온프레미스 환경을 위한 Cursor-style AI 코딩 서비스 API 명세입니다.

### 보안 원칙
- 모든 경로는 상대 경로만 허용 (절대 경로, `../` 탈출 금지)
- 워크스페이스 격리 (다른 workspace 접근 차단)
- 프롬프트/응답 원문 로그 저장 금지 (hash만 저장)

### 에러 응답 형식
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "detail": "Optional detail"
}
```

---

## Auth

### GET /api/auth/me

현재 인증된 사용자 정보를 반환합니다.

**응답**: `UserResponse`
```json
{
  "userId": "u_demo",
  "name": "Demo User",
  "orgId": "org_demo"
}
```

**에러 코드**:
- `401`: Unauthorized

**TODO**: SSO/LDAP 연동 구현

---

## Workspaces

### POST /api/workspaces

새 워크스페이스를 생성합니다.

**요청**: `CreateWorkspaceRequest`
```json
{
  "name": "my-project",
  "language": "python"
}
```

**응답**: `WorkspaceResponse` (201 Created)
```json
{
  "workspaceId": "ws_my-project",
  "name": "my-project",
  "rootPath": "/workspaces/ws_my-project"
}
```

**에러 코드**:
- `400`: Invalid request (이름 형식 오류)
- `401`: Unauthorized
- `409`: Workspace already exists

**TODO**: 실제 파일시스템 디렉토리 생성, 권한 설정, DB 저장

---

### GET /api/workspaces

사용자가 접근 가능한 워크스페이스 목록을 반환합니다.

**응답**: `List[WorkspaceResponse]`
```json
[
  {
    "workspaceId": "ws_demo",
    "name": "demo-project",
    "rootPath": "/workspaces/ws_demo"
  }
]
```

**에러 코드**:
- `401`: Unauthorized

**TODO**: DB에서 사용자별 목록 조회, 페이지네이션

---

## Files

### GET /api/workspaces/{wsId}/files

워크스페이스의 파일 트리를 반환합니다.

**경로 파라미터**:
- `wsId`: 워크스페이스 ID

**응답**: `FileTreeResponse`
```json
{
  "workspaceId": "ws_demo",
  "tree": [
    {
      "name": "src",
      "path": "src",
      "type": "directory",
      "children": [
        {
          "name": "main.py",
          "path": "src/main.py",
          "type": "file"
        }
      ]
    }
  ]
}
```

**에러 코드**:
- `401`: Unauthorized
- `403`: Forbidden (워크스페이스 접근 권한 없음)
- `404`: Workspace not found

**TODO**: 실제 파일시스템 읽기, `.gitignore` 적용

---

### GET /api/workspaces/{wsId}/files/content

지정된 파일의 내용을 반환합니다.

**경로 파라미터**:
- `wsId`: 워크스페이스 ID

**쿼리 파라미터**:
- `path` (required): 파일 경로 (workspace 기준 상대 경로)

**응답**: `FileContentResponse`
```json
{
  "path": "src/main.py",
  "content": "print('hello')\n",
  "encoding": "utf-8"
}
```

**에러 코드**:
- `400`: Invalid path (경로 탈출 시도)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: File not found

**TODO**: 실제 파일 읽기, 인코딩 감지, 바이너리 파일 처리

---

### PUT /api/workspaces/{wsId}/files/content

지정된 파일의 내용을 수정합니다.

**경로 파라미터**:
- `wsId`: 워크스페이스 ID

**요청**: `UpdateFileContentRequest`
```json
{
  "path": "src/main.py",
  "content": "print('updated')\n"
}
```

**응답**: `UpdateFileContentResponse`
```json
{
  "path": "src/main.py",
  "success": true,
  "message": "File updated"
}
```

**에러 코드**:
- `400`: Invalid request (경로 탈출 시도)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: File not found

**⚠️ 주의**: AI 기반 코드 변경은 이 API를 사용하지 않고 `/patch/apply`를 사용해야 합니다.

**TODO**: 실제 파일 쓰기, 백업 생성, 감사 로그

---

## AI

### POST /api/ai/explain

선택된 코드에 대한 AI 설명을 반환합니다.

**요청**: `AIExplainRequest`
```json
{
  "workspaceId": "ws_demo",
  "filePath": "src/main.py",
  "selection": {
    "startLine": 10,
    "endLine": 15
  }
}
```

**응답**: `AIExplainResponse`
```json
{
  "explanation": "이 코드는 ...",
  "tokensUsed": 150
}
```

**에러 코드**:
- `400`: Invalid request (경로 오류)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: File not found
- `503`: LLM service unavailable

**흐름**: API → Context Builder → vLLM → 응답

**TODO**: Context Builder 연동, vLLM 호출

---

### POST /api/ai/rewrite

지시사항에 따라 코드를 수정하고 unified diff를 반환합니다.

**요청**: `AIRewriteRequest`
```json
{
  "workspaceId": "ws_demo",
  "instruction": "이 함수를 async로 변경해줘",
  "target": {
    "file": "src/api.py",
    "selection": {
      "startLine": 10,
      "endLine": 12
    }
  }
}
```

**응답**: `AIRewriteResponse`
```json
{
  "diff": "--- a/src/api.py\n+++ b/src/api.py\n@@ -10,3 +10,3 @@\n-def fetch():\n+async def fetch():\n     ...",
  "tokensUsed": 200
}
```

**에러 코드**:
- `400`: Invalid request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: File not found
- `503`: LLM service unavailable

**⚠️ 중요**: 이 API는 diff만 반환합니다. 실제 적용은 `/patch/validate` → `/patch/apply`를 통해 수행해야 합니다.

**흐름**: API → Context Builder → vLLM → diff 반환 → (클라이언트) → `/patch/validate` → `/patch/apply`

**TODO**: Context Builder 연동, vLLM 호출 (rewrite 템플릿 사용)

---

## Patch

### POST /api/patch/validate

unified diff 패치의 유효성을 검증합니다.

**요청**: `PatchValidateRequest`
```json
{
  "workspaceId": "ws_demo",
  "patch": "--- a/src/main.py\n+++ b/src/main.py\n@@ -1,1 +1,1 @@\n-old\n+new"
}
```

**응답**: `PatchValidateResponse`
```json
{
  "valid": true,
  "reason": null,
  "files": ["src/main.py"]
}
```

**에러 코드**:
- `400`: Invalid request
- `401`: Unauthorized
- `403`: Forbidden

**검증 항목**:
1. diff 형식 유효성
2. 경로 탈출 시도 (`../`)
3. 파일 확장자 allowlist
4. 패치 크기 제한
5. 워크스페이스 내 파일인지 확인

**TODO**: `packages/diff-utils` 연동 (Task C)

---

### POST /api/patch/apply

검증된 패치를 실제 파일에 적용합니다.

**요청**: `PatchApplyRequest`
```json
{
  "workspaceId": "ws_demo",
  "patch": "--- a/src/main.py\n+++ b/src/main.py\n@@ -1,1 +1,1 @@\n-old\n+new",
  "dryRun": false
}
```

**응답**: `PatchApplyResponse`
```json
{
  "success": true,
  "appliedFiles": ["src/main.py"],
  "message": "Patch applied"
}
```

**에러 코드**:
- `400`: Invalid patch
- `401`: Unauthorized
- `403`: Forbidden
- `404`: File not found
- `409`: Conflict (패치 적용 불가)

**⚠️ 중요 (AGENTS.md 규칙)**: 코드 변경은 반드시 이 API를 통해서만 적용해야 합니다.

**흐름**:
1. 패치 검증 (`/patch/validate`와 동일)
2. `dryRun=true`인 경우 여기서 종료
3. 파일 백업 생성 (옵션)
4. 패치 적용
5. 감사 로그 기록 (해시만)

**TODO**: `packages/diff-utils`의 `applyPatchToText` 사용, 트랜잭션 처리, 충돌 감지

---

## WebSocket

### WS /ws/workspaces/{wsId}

워크스페이스 실시간 협업을 위한 WebSocket 연결.

**경로 파라미터**:
- `wsId`: 워크스페이스 ID

**연결**:
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/workspaces/ws_demo");
```

**메시지 타입**:

#### 1. file_change
파일 변경 알림
```json
{
  "type": "file_change",
  "payload": {
    "file": "src/main.py",
    "event": "modified"
  }
}
```

#### 2. cursor_move
커서 이동 (협업용)
```json
{
  "type": "cursor_move",
  "payload": {
    "userId": "u_demo",
    "file": "src/main.py",
    "line": 10,
    "column": 5
  }
}
```

#### 3. ai_stream
AI 응답 스트리밍
```json
{
  "type": "ai_stream",
  "payload": {
    "chunk": "This code...",
    "done": false
  }
}
```

#### 4. error
에러 메시지
```json
{
  "type": "error",
  "payload": {
    "error": "Error message",
    "code": "ERROR_CODE"
  }
}
```

**에러 코드**:
- `1008`: Policy violation (인증 실패)

**TODO**: 
- 인증 토큰 검증
- 파일 변경 감지 및 브로드캐스트
- AI 응답 스트리밍
- Redis pub/sub으로 다중 인스턴스 지원

---

## 상태 코드

| 코드 | 의미 | 사용 예 |
|------|------|---------|
| `200` | OK | 성공적인 조회 |
| `201` | Created | 워크스페이스 생성 |
| `400` | Bad Request | 잘못된 요청 (입력 검증 실패) |
| `401` | Unauthorized | 인증 필요 |
| `403` | Forbidden | 권한 없음 |
| `404` | Not Found | 리소스 없음 |
| `409` | Conflict | 충돌 (중복, 패치 적용 불가) |
| `413` | Payload Too Large | 파일 크기 초과 |
| `500` | Internal Server Error | 서버 오류 |
| `503` | Service Unavailable | LLM 서비스 불가 |

---

## 참고

- **아키텍처**: `docs/architecture.md`
- **Context Builder**: `docs/context-builder.md`
- **AGENTS 규칙**: `AGENTS.md`
- **온프레미스 Runbook**: `docs/runbook-onprem.md`
