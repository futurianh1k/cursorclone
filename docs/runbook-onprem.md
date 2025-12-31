# On-Prem Runbook (PoC)

## 네트워크
- LLM 노드는 outbound 차단
- API/Web은 내부망에서만 접근
- 필요 시 mTLS 적용

## 로그/감사
- prompt/응답 원문 저장 금지
- 저장: hash + user/workspace/action/timestamp + patch hash
- Audit DB(PostgreSQL) 권장

## 권한(RBAC)
- AI-Modify 권한 분리(기본 Off)
