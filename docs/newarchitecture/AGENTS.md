# AGENTS.md — v0.3

## Non-negotiables
1) 외부 인터넷 의존성 추가 금지
2) Workspace -> AI Gateway 단일 경유 유지
3) Workspace 사용자 토큰을 Upstream에 전달 금지(Upstream auth 분리)
4) JWKS는 캐시/리프레시 전략 적용, FAIL_OPEN 설정은 승인된 경우만 true
5) 스트리밍 DLP 정책은 환경변수로 선택 가능하되 기본은 pre_only
6) 감사 DB: 월별 파티셔닝 + retention purge 절차(운영 승인/키 보호)
7) OpenAPI 스펙은 pinned openapi.json과 verify로 drift 방지

## v0.3 Done
- JWKS 백그라운드 refresh 동작 + TTL
- Upstream auth mode(static_bearer/mtls) 동작
- 스트리밍 DLP 모드 설명/구현 일치
- audit_events 파티셔닝 및 partition 자동 생성
- openapi.json 생성/검증 스크립트 제공
