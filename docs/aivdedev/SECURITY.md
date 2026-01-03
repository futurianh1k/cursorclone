# Security Specification (금융권 제출용)

## 1. 인증/인가
- SSO(OIDC) + MFA
- 사용자/프로젝트 RBAC

## 2. 격리
- 1 User = 1 IDE Instance
- 네트워크 Namespace 분리

## 3. 데이터 보호
- 프롬프트 외부 반출 차단
- 로그 마스킹 정책

## 4. 감사
- 접속/세션/관리자 로그 중앙 수집