# 브라우저 기반 VS Code 웹 IDE 전환 계획

**날짜**: 2026-01-03  
**브랜치**: `feature/browser-vscode-webide`  
**상태**: 계획 수립 완료

---

## 1. 요청자(사용자) 요구사항 요약

사용자가 웹브라우저에서 로그인하고 대시보드에서 워크스페이스를 만들 때:
1. **브라우저 기반 VS Code 서버 웹 IDE**를 구동
2. 웹 IDE에서 **Cursor 수준의 AI 코딩 지원** 제공
3. 웹 IDE에서 **빌드, 디버깅 등 터미널 구동**하여 개발 가능

### 핵심 요구사항
- Monaco 기반 자체 IDE → **code-server (VS Code 서버)** 전환
- AI 자동완성: **Tabby** 확장 프로그램
- AI Chat/Edit/Agent: **Continue** 확장 프로그램
- 사용자별 격리된 IDE 컨테이너
- 금융권 보안/감사 요구사항 충족

---

## 2. Assistant 응답 내용 (계획)

### 분석된 문서
- `docs/aivdedev/` 폴더의 모든 MD 파일 분석 완료
- PDF 파일 참조 (브라우저기반VSCode서버웹IDE구축가이드.pdf)

### 주요 변경점

| 구분 | 현재 | 변경 후 |
|------|------|---------|
| Web IDE | Next.js + Monaco | **code-server** |
| AI Autocomplete | vLLM 직접 호출 | **Tabby Extension** |
| AI Chat/Edit | 자체 AIChat | **Continue Extension** |
| 사용자 격리 | 폴더 분리 | **1 User = 1 Container** |
| 인증 | JWT | **SSO(OIDC) + MFA** |

### 새로운 아키텍처

```
사용자 브라우저
       │
       ▼
Reverse Proxy (SSO 인증)
       │
   ┌───┴───┐
   ▼       ▼
Dashboard  User IDE Containers
(Next.js)  ├── user-1-ws-abc (code-server)
   │       ├── user-2-ws-xyz (code-server)
   │       └── ...
   ▼
API Server ──▶ AI Gateway ──▶ Tabby/vLLM
```

---

## 3. 실제로 수행한 변경 내용

### 3.1 브랜치 생성
```bash
git checkout -b feature/browser-vscode-webide
```

### 3.2 작성된 문서

| 파일 | 설명 |
|------|------|
| `docs/architecture-comparison.md` | 현재 vs 목표 아키텍처 상세 비교 분석 |
| `history/2026-01-03_browser-vscode-webide.md` | 본 변경 이력 문서 |

---

## 4. 구현 계획

### Phase 1: 기본 WebIDE 전환 (1-2주)
- [ ] code-server Docker 이미지 생성
- [ ] IDE 컨테이너 프로비저닝 API 구현
- [ ] 대시보드 → IDE 리다이렉트 구현
- [ ] Traefik 동적 라우팅 설정

### Phase 2: AI 확장 통합 (1-2주)
- [ ] Tabby Server 배포
- [ ] Tabby Extension 사전 설치
- [ ] Continue Extension 사전 설치
- [ ] AI Gateway 확장 (Tabby/Continue 호환 API)

### Phase 3: 보안/운영 강화 (1-2주)
- [ ] SSO(OIDC) 연동
- [ ] 감사 로깅 강화
- [ ] 정책 엔진 구현 (Rate Limit, 파일 범위 제한)

---

## 5. 테스트 및 검증 방법

### 5.1 기능 테스트
- [ ] 대시보드에서 워크스페이스 생성 시 IDE 컨테이너 자동 생성
- [ ] IDE 접속 후 터미널에서 빌드/디버깅 가능
- [ ] Tabby 자동완성 동작 확인 (P95 < 300ms)
- [ ] Continue Chat/Edit 동작 확인

### 5.2 보안 테스트
- [ ] 사용자간 컨테이너 격리 검증
- [ ] 감사 로그 생성 확인
- [ ] SSO 인증 흐름 검증

### 5.3 성능 테스트
- [ ] 동시 10명 사용자 IDE 컨테이너 생성
- [ ] AI 응답 지연시간 측정

---

## 6. 향후 작업 및 주의사항

### 주의사항
1. **기존 기능 유지**: 현재 Monaco 기반 IDE도 당분간 병행 운영
2. **데이터 마이그레이션**: 기존 워크스페이스 데이터 호환성 유지
3. **리소스 관리**: 컨테이너당 CPU/메모리 제한 설정 필수
4. **보안**: 컨테이너 탈출 방지, 네트워크 격리 검증

### 참고 문서
- `docs/aivdedev/` - 전체 설계 문서
- `docs/architecture-comparison.md` - 상세 비교 분석

---

## 7. 관련 커밋

- 초기 계획 수립 및 문서 작성 (현재)
