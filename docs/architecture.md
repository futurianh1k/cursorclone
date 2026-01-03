# Architecture (On-Prem PoC)

- Web IDE(Next.js + Monaco) → API(FastAPI) → Workspace Manager → Docker Containers → LLM(vLLM)
- 코드 변경은 Diff 기반 Patch로만 반영한다.
- Audit Log는 원문 저장 금지(해시 + 메타만).
- 각 워크스페이스는 독립적인 Docker 컨테이너로 격리 실행 (향후 구현)

## 현재 구현 (MVP)
- 파일시스템 기반 워크스페이스
- GitHub 클론 기능
- 기본 보안 검증

## 향후 구현 (Phase 2)
- Docker 컨테이너 기반 워크스페이스 격리
- 명령 실행 API (컨테이너 내부)
- 리소스 모니터링 및 제한
- 자동 비활성화/재시작

## MVP API
- /auth/me (stub)
- /workspaces (CRUD, GitHub clone)
- /files (tree, read, write)
- /ai/explain
- /ai/rewrite (diff 반환)
- /patch/validate
- /patch/apply
- WS: /ws/workspaces/{wsId}

## 향후 API (Phase 2)
- /workspaces/{ws_id}/execute (컨테이너 내 명령 실행)
- /workspaces/{ws_id}/status (컨테이너 상태 조회)
- /workspaces/{ws_id}/logs (컨테이너 로그 조회)

## 관리자 API (완료)
- POST /api/admin/servers (서버 등록)
- GET /api/admin/servers (서버 목록)
- POST /api/admin/servers/{id}/test (연결 테스트)
- POST /api/admin/workspaces/{id}/place (워크스페이스 배치)

## 스케일링 아키텍처 (500명 규모)

### 현재 구현 (Phase 1)
- ✅ 데이터베이스 스키마 설계 (멀티 테넌트 지원)
- ✅ Redis 캐싱 레이어
- ✅ 비동기 데이터베이스 연결 풀
- ✅ 서비스 레이어 분리 (비즈니스 로직 분리)

### 향후 구현 (Phase 2-3)
- [ ] Kubernetes 기반 워크스페이스 관리
- [ ] 자동 스케일링 (HPA)
- [ ] 리소스 모니터링
- [ ] 고가용성 구성

**상세 설계**: `docs/scalability-architecture.md` 참조

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│                    Web IDE (Next.js)                     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/WebSocket
                       ▼
┌─────────────────────────────────────────────────────────┐
│              API Server (FastAPI)                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │      Workspace Manager (향후 구현)                │  │
│  │  - 컨테이너 생성/삭제/관리                        │  │
│  │  - 명령 실행                                       │  │
│  │  - 리소스 모니터링                                │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │      Context Builder                              │  │
│  └──────────────────────┬───────────────────────────┘  │
└─────────────────────────┼──────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Container   │  │  Container   │  │  Container   │
│  ws_001      │  │  ws_002      │  │  ws_003      │
│  (향후 구현) │  │  (향후 구현) │  │  (향후 구현) │
└──────────────┘  └──────────────┘  └──────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                          ▼
                ┌─────────────────┐
                │   vLLM (GPU)   │
                └─────────────────┘
```

**참고**: 상세 설계는 `docs/workspace-container-architecture.md` 참조
