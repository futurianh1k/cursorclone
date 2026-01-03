# VDE Web IDE Platform - 단계별 체크리스트

## PoC 체크리스트

### 인프라 준비
- [ ] GPU 서버 확보 (최소 RTX 4090 1대, A100 1대)
- [ ] 일반 서버 확보 (4 vCPU, 8GB RAM 이상)
- [ ] 네트워크 구성 (VLAN, 방화벽 규칙)
- [ ] Docker/Docker Compose 설치
- [ ] NVIDIA Container Toolkit 설치

### 소프트웨어 준비
- [ ] 컨테이너 이미지 다운로드/미러링
  - [ ] codercom/code-server:4.96.4
  - [ ] tabbyml/tabby:0.21.0
  - [ ] vllm/vllm-openai:v0.6.6
  - [ ] ghcr.io/berriai/litellm:main-latest
  - [ ] quay.io/keycloak/keycloak:23.0
- [ ] AI 모델 파일 반입
  - [ ] StarCoder2-7B (Tabby용)
  - [ ] DeepSeek-Coder-6.7B-Instruct (Chat용)
- [ ] VS Code 확장 VSIX 준비
  - [ ] Continue
  - [ ] Tabby

### 기능 검증
- [ ] code-server 브라우저 접속
- [ ] Keycloak 로그인 연동
- [ ] Tabby 자동완성 동작
  - [ ] Python 자동완성
  - [ ] JavaScript/TypeScript 자동완성
  - [ ] 응답시간 < 400ms (P95)
- [ ] Continue 확장 동작
  - [ ] 설치 및 로딩
  - [ ] Chat 기능
  - [ ] Edit 기능
  - [ ] WebSocket 연결 안정성
- [ ] Git 연동
  - [ ] Clone
  - [ ] Commit/Push

### 성능 검증
- [ ] 자동완성 응답시간 측정
- [ ] Chat 응답시간 측정
- [ ] IDE 로딩시간 측정
- [ ] 동시 사용자 5명 테스트

### PoC 완료 기준
- [ ] 자동완성 P95 < 400ms
- [ ] Chat P95 < 5s
- [ ] Continue 핵심 기능 동작
- [ ] 사용자 만족도 3.5/5 이상
- [ ] 치명적 호환성 이슈 없음

---

## Pilot 체크리스트

### 보안 강화
- [ ] SSO 연동 (Keycloak → 사내 IDP)
- [ ] MFA 강제 적용
- [ ] 세션 타임아웃 설정 (30분)
- [ ] 동시 세션 제한 (1세션)
- [ ] IP 허용 목록 적용
- [ ] TLS 적용 (사내 PKI)

### 워크스페이스 격리
- [ ] 사용자별 네임스페이스
- [ ] NetworkPolicy 적용
- [ ] ResourceQuota 설정
- [ ] PVC 프로비저닝 자동화

### 공급망 통제
- [ ] 확장 화이트리스트 정의
- [ ] 내부 VSIX 저장소 구성
- [ ] 확장 설치 제한 설정
- [ ] 확장 설치 감사 로깅
- [ ] Nexus 패키지 미러 구성
  - [ ] PyPI 미러
  - [ ] npm 미러
  - [ ] apt 미러
- [ ] pip/npm 설정 강제

### LLM Gateway
- [ ] LiteLLM Proxy 설치
- [ ] 모델 라우팅 설정
- [ ] Rate limiting 설정
- [ ] 메타데이터 로깅 설정
- [ ] DLP 룰 적용

### 감사 로깅
- [ ] 인증 로그 수집
- [ ] 접근 로그 수집 (Nginx)
- [ ] 시스템 감사 로그 (auditd)
- [ ] IDE 세션 로그
- [ ] AI 요청 메타데이터 로그
- [ ] SIEM 연동

### 파일럿 운영
- [ ] 20-30명 사용자 온보딩
- [ ] 사용 가이드 배포
- [ ] 헬프데스크 체계 구축
- [ ] 모니터링 대시보드 구축
- [ ] 알림 설정

### Pilot 완료 기준
- [ ] 보안 체크리스트 100% 충족
- [ ] 99% 가동률 (1주 기준)
- [ ] 보안팀 승인 획득
- [ ] 사용자 만족도 4/5 이상
- [ ] 운영 절차서 완성

---

## Production 체크리스트

### Kubernetes 구성
- [ ] 프로덕션 클러스터 구성
- [ ] 노드 풀 구성 (GPU, General)
- [ ] Ingress Controller 설정
- [ ] Storage Class 설정
- [ ] PodDisruptionBudget 설정

### 고가용성
- [ ] Nginx Active-Standby
- [ ] Keycloak 클러스터
- [ ] Tabby 다중 인스턴스
- [ ] vLLM 다중 인스턴스
- [ ] 장애 복구 테스트

### 자동화
- [ ] ArgoCD GitOps 파이프라인
- [ ] HPA 설정 (code-server)
- [ ] 예약 스케일링 (업무시간)
- [ ] Velero 백업 설정
- [ ] 백업 복구 테스트

### 전사 롤아웃
- [ ] 1차 롤아웃: 50명
- [ ] 안정화 확인 (1주)
- [ ] 2차 롤아웃: 100명
- [ ] 안정화 확인 (1주)
- [ ] 전사 롤아웃 (필요시)

### 운영 전환
- [ ] 운영팀 인수인계
- [ ] On-call 체계 구축
- [ ] SLA 정의 및 모니터링
- [ ] 문서 최종 업데이트

---

## 보안 심사 체크리스트 (금융권)

### 접근통제
- [ ] SSO 연동 완료
- [ ] MFA 강제 적용
- [ ] 세션 타임아웃 설정 (30분 이하)
- [ ] 동시 세션 제한 (1세션)
- [ ] IP 허용 목록 적용
- [ ] 사용자별 워크스페이스 격리

### 데이터 보호
- [ ] 인터넷 접근 완전 차단
- [ ] 파일 반출입 통제
- [ ] LLM 프롬프트 사내 Gateway만 허용
- [ ] DLP 룰 적용
- [ ] 민감정보 마스킹

### 공급망
- [ ] 확장 화이트리스트 운영
- [ ] 패키지 미러 구성
- [ ] 모델 반입 절차 수립
- [ ] SBOM 생성
- [ ] 컨테이너 이미지 스캔

### 감사
- [ ] 인증 로그 수집
- [ ] 접근 로그 수집
- [ ] 시스템 감사 로그 (auditd)
- [ ] IDE 세션 로그
- [ ] AI 요청 메타데이터 로그
- [ ] SIEM 연동
- [ ] 로그 보존 정책 (1년)

### 취약점 관리
- [ ] 정기 취약점 스캔 일정 수립
- [ ] 패치 정책 문서화
- [ ] Critical 취약점 24시간 내 대응 체계
