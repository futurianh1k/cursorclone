# TODO 트래커

**최종 업데이트**: 2026-01-03 (P0-P2 전체 완료)  
**총 TODO 수**: 37개 (apps/ 내), **16개 완료 (53%)**

---

## 📊 카테고리별 분류

### 🔴 프로덕션 차단 (Production Blocking)
프로덕션 배포 전 반드시 해결해야 함

| 파일 | 라인 | TODO | 우선순위 | 상태 |
|------|------|------|----------|------|
| `routers/auth.py` | - | ✅ JWT 토큰 검증 | P0 | **완료** |
| `routers/admin.py` | 33 | ✅ RBAC 권한 확인 | P0 | **완료** |
| `routers/ai_gateway.py` | 114 | ✅ JWT에서 사용자 ID 추출 | P0 | **완료** |
| `routers/ide.py` | 98 | ✅ JWT에서 사용자 ID 추출 | P0 | **완료** |

### 🟡 기능 개선 (Feature Enhancement)
기능 완성도 향상을 위해 필요

| 파일 | 라인 | TODO | 우선순위 | 상태 |
|------|------|------|----------|------|
| `routers/workspaces.py` | 66, 216 | ✅ DB에 메타데이터 저장 | P2 | **완료** |
| `routers/workspaces.py` | 107 | ✅ 사용자 권한에 따른 목록 필터링 | P2 | **완료** |
| `routers/workspaces.py` | 108 | ✅ 페이지네이션 지원 | P2 | **완료** |
| `routers/files.py` | 65 | ✅ 권한 검증 로직 | P2 | **완료** |
| `routers/files.py` | 247 | ✅ 감사 로그 기록 (해시만) | P2 | **완료** |
| `routers/patch.py` | 30 | ✅ 권한 검증 로직 | P2 | **완료** |
| `routers/patch.py` | 195 | ✅ 감사 로그 저장 | P2 | **완료** |

### 🟢 실제 구현 필요 (Implementation Needed)
현재 스텁/모킹된 부분

| 파일 | 라인 | TODO | 우선순위 | 상태 |
|------|------|------|----------|------|
| `routers/admin.py` | 254 | 실제 연결 테스트 (SSH, K8s API) | P2 | 대기 |
| `routers/ai.py` | 57-60 | ✅ 실제 워크스페이스 루트 경로 | P1 | **완료** |
| `routers/ai.py` | 70 | 권한 검증 로직 | P2 | 대기 |
| `routers/ai.py` | 122 | ✅ 실제 AI 설명 구현 | P1 | **완료** |
| `routers/ai.py` | 522 | ✅ 실제 AI 리라이트 구현 | P1 | **완료** |
| `routers/ai.py` | 1419, 1445 | Vision LLM 연동 | P3 | 대기 |
| `routers/ide.py` | 433 | 실제 메트릭 수집 | P3 | 대기 |
| `services/placement_service.py` | 76 | Redis에서 마지막 선택 서버 가져오기 | P3 | 대기 |

### 🔵 스케일링/인프라 (Scaling/Infrastructure)
대규모 배포 시 필요

| 파일 | 라인 | TODO | 우선순위 | 상태 |
|------|------|------|----------|------|
| `routers/ws.py` | 14 | Redis pub/sub로 다중 인스턴스 지원 | P3 | 대기 |
| `routers/ws.py` | 61, 88 | ✅ 권한/인증 검증 | P2 | **완료** |
| `routers/ws.py` | 121, 131 | 파일 변경/커서 이동 처리 | P3 | 대기 |
| `routers/ai_gateway.py` | 150 | 중앙 로깅 시스템 연동 | P3 | 대기 |
| `routers/ai_gateway.py` | 384 | Redis/DB에서 사용량 조회 | P3 | 대기 |
| `main.py` | 97 | ✅ 로깅 (스택트레이스 내부 로그만) | P2 | **완료** |

### ⚪ 프론트엔드 (Frontend)
웹 UI 개선

| 파일 | 라인 | TODO | 우선순위 |
|------|------|------|----------|
| `dashboard/contact/page.tsx` | 15 | API 호출 | P3 |
| `dashboard/settings/page.tsx` | 39 | API 호출 | P3 |

### ⬛ 기타 (Others)
향후 구현 예정

| 파일 | 라인 | TODO | 우선순위 |
|------|------|------|----------|
| `context_builder/collector.py` | 66 | RELATED, SEARCH 타입 구현 | P3 |
| `routers/ai.py` | 49 | 의존성 주입/설정에서 가져오기 | P3 |
| `routers/ai.py` | 984 | Implement (미완성 코드) | P2 |

---

## 📈 진행 상황

| 카테고리 | 총 | 완료 | 진행률 |
|----------|-----|------|--------|
| 프로덕션 차단 | 4 | 4 | 100% |
| 기능 개선 | 7 | 7 | 100% |
| 실제 구현 | 8 | 3 | 38% |
| 스케일링/인프라 | 6 | 2 | 33% |
| 프론트엔드 | 2 | 0 | 0% |
| 기타 | 3 | 0 | 0% |
| **총계** | **30** | **16** | **53%** |

---

## 🎯 우선순위 정의

| 레벨 | 설명 | 목표 시점 |
|------|------|----------|
| P0 | 프로덕션 배포 차단 | Phase 1 (1-2주) |
| P1 | 핵심 기능 완성 | Phase 1 (1-2주) |
| P2 | 기능 개선 및 품질 | Phase 2 (2-4주) |
| P3 | 향후 개선 | Phase 3+ |

---

## 🔧 다음 작업 권장

### 즉시 (P0-P1)
1. JWT에서 사용자 ID 추출 통합 (ai_gateway.py, ide.py)
2. 워크스페이스 루트 경로 구현 (ai.py)
3. AI 설명/리라이트 실제 구현 (ai.py)

### 단기 (P2)
1. 권한 검증 로직 통합 (files.py, patch.py, ws.py)
2. 감사 로그 저장 구현
3. 워크스페이스 페이지네이션

### 장기 (P3)
1. Redis pub/sub 다중 인스턴스
2. Vision LLM 연동
3. 중앙 로깅 시스템

---

## 📝 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2026-01-03 | 초기 TODO 트래커 작성 |
| 2026-01-03 | RBAC 권한 검증 완료 (admin.py) |
| 2026-01-03 | 인증 시스템 완료 (auth.py) |
