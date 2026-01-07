# PRD — AI Coding Workspace Platform (금융권 VDE)
버전: v0.3  

목적: 금융권 폐쇄망(VDE) 환경에서 **AI 코딩 생산성**을 제공하면서도  
보안·감사·통제 요건을 충족하는 Web IDE + AI Gateway 플랫폼 구축

---

## 1. 배경 및 문제 정의
- 금융권은 외부 SaaS IDE 및 LLM 사용 불가
- 개발자는 Cursor/Codex 수준의 AI 코딩 경험 요구
- IDE·AI·모델이 직접 연결되면 감사/비용/유출 통제 불가

---

## 2. 목표
### 2.1 비즈니스 목표
- 개발 생산성 향상(코드 작성/리팩터링/리뷰 자동화)
- 금융권 규제 준수 상태에서 AI 도입

### 2.2 기술 목표
- Workspace 경량·불변
- AI Gateway 단일 통제 지점
- 모든 AI 행위 감사 가능

---

## 3. 범위 (In / Out)
### In Scope
- code-server 기반 Web IDE
- AI Gateway(FastAPI)
- Tabby / Agent / Chat / RAG 연동
- JWT/JWKS 인증
- DLP, 감사 로그, 비용 추적

### Out of Scope
- IDE 로컬 설치
- 외부 SaaS LLM 직접 연동
- 사용자 임의 플러그인 설치

---

## 4. 사용자 유형
| 유형 | 설명 |
|---|---|
| Developer | IDE + AI 사용 |
| Admin | 정책/운영 관리 |
| Auditor | 로그/감사 확인 |

---

## 5. 기능 요구사항
### 5.1 Workspace
- 웹 브라우저 기반 IDE
- 사전 설치 확장만 사용 가능
- 외부 네트워크 차단

### 5.2 AI Gateway
- JWT 인증 + Role 인가
- Upstream Auth 분리
- Streaming/SSE 지원
- DLP 사전/점진 검사
- Diff hash 기반 코드 변경 추적

---

## 6. 비기능 요구사항
### 6.1 보안
- JWKS 캐시/리프레시
- mTLS 또는 내부 토큰
- DLP 정책 외부화

### 6.2 감사/규제
- 감사 로그 DB 적재
- 월별 파티셔닝
- Retention/ILM 정책

### 6.3 운영
- 무중단 배포
- OpenAPI 스펙 고정
- 장애 시 IDE 기본 기능 유지

---

## 7. 성공 기준 (DoD)
- 금융권 보안 심사 통과
- AI 요청 100% Gateway 경유
- 모든 AI 변경 Diff hash 추적 가능
- 운영 환경에서 장애 없는 스트리밍

---

## 8. 산출물
- PRD.md
- docs/*.md
- gateway(FastAPI)
- infra/K8s 매니페스트
- 제출용 보안/기술 설계서

---

본 PRD는 Cursor / Codex / Claude Code가  
**구현 기준으로 삼아야 하는 최상위 문서**이다.
