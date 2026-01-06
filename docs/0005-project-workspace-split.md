## 대화/요청
- 사용자는 `project_id(pid)`와 `workspace_id(wid)`를 분리하고, **1 Project : N Workspaces** 를 지원하도록 DB/토큰/감사 흐름을 정리해달라고 요청.
- DB 수정 허용.

## 결정 사항(설계)
- `projects(project_id)` 테이블을 신설하고 `workspaces.project_id` FK를 추가한다.
- 기존 데이터는 **workspace별 1 project**로 자동 승격(backfill)하여 기존 사용 흐름을 깨지 않는다.
- Gateway 토큰은 `tid/pid/wid/role` 클레임을 유지하되, `pid != wid`를 전제한다.
- IDE(code-server)는 워크스페이스별 설정 파일을 마운트하는 방식으로 토큰을 주입하므로, pid/wid 분리를 그대로 반영한다.

## 구현 요약
- DB: `projects` 테이블 + `workspaces.project_id` NOT NULL + FK/인덱스
- API:
  - `POST /api/projects`, `GET /api/projects`, `GET /api/projects/{project_id}`
  - `POST /api/workspaces`에 `projectId`(옵션) 지원
- 토큰:
  - `POST /api/auth/gateway-token`에서 `ws.project_id`를 pid로 사용

## 테스트
- `pytest apps/api/tests/test_gateway_jwks.py`

