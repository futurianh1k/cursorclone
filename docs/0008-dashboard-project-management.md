## 요청
- 프로젝트 카드 상단에서 “프로젝트 이름 수정/삭제(프로젝트 관리)” UX 추가

## 구현 요약
- API
  - `PATCH /api/projects/{projectId}`: 프로젝트 이름 변경
  - `DELETE /api/projects/{projectId}`: 프로젝트 삭제
    - 프로젝트에 워크스페이스가 존재하면 `409 PROJECT_NOT_EMPTY`로 차단
- Web
  - 프로젝트 카드 헤더에 **이름 변경(인라인 편집/저장/취소)** 추가
  - 프로젝트 카드 헤더에 **삭제(확인 2단계)** 추가
    - 워크스페이스가 있으면 삭제를 UI에서도 차단(안내 메시지)
  - 프로젝트가 비어 있어도(워크스페이스 0개) 카드가 표시되도록 그룹핑 유틸 수정

## 코드
- API
  - `apps/api/src/routers/projects.py`
  - `apps/api/src/models/base.py`, `apps/api/src/models/__init__.py`
- Web
  - `apps/web/src/app/dashboard/page.tsx`
  - `apps/web/src/lib/api.ts`
  - `apps/web/src/lib/projectGrouping.ts`
  - `apps/web/src/__tests__/api.test.ts`

## 테스트
- Web: `cd apps/web && npm test`
- API: 로컬 환경 의존성 차이로 전체 pytest는 일부 실패할 수 있으나(기존 이슈), 본 변경은 단위/타입 체크 및 web 테스트로 검증

