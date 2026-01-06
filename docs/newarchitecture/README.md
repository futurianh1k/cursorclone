# AI Coding Workspace Platform — v0.3 (금융권 제출/운영 배포 강화)

작성일: 2026-01-06

v0.3는 v0.2를 기반으로 금융권 제출/운영 배포 수준으로 강화한 **AI Gateway 참조 구현**입니다.

강화 항목:
1) JWKS 캐시/리프레시 전략(백그라운드 refresh + fail-open/close 정책 선택)
2) Upstream auth 분리(내부 서비스 토큰 또는 mTLS/서비스 메시 전제) — Workspace 토큰을 업스트림에 전달하지 않음
3) 스트리밍(DLP) 정책 명확화: 사전(pre) 검사 + 점진(incremental) 검사 옵션화
4) 감사 테이블 파티셔닝/보관주기(ILM): 월별 파티션 + retention job 설계
5) OpenAPI 스펙 자동 생성 및 고정(openapi.json 생성/검증 스크립트)

빠른 시작은 `gateway/README.md` 참고.
