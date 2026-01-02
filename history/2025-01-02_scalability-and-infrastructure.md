# 2025-01-02 - 대규모 스케일링 및 인프라 관리 설계

## 사용자 요구사항

1. **대규모 스케일링 고려**
   - 500명 규모의 조직을 위한 서비스로 스케일링
   - 컨테이너 기반 워크스페이스 아키텍처 필요성 인식

2. **관리자 대시보드**
   - 컨테이너 저장 서버 주소/폴더 위치 선택 기능
   - 서버 접속 인증 및 신원 증명을 상용 SaaS 수준으로 설계

## 구현 답변

### 1. 대규모 스케일링 아키텍처 설계

**문서 작성**:
- `docs/scalability-architecture.md`: 500명 규모를 위한 전체 아키텍처 설계
  - Kubernetes 기반 아키텍처
  - 멀티 테넌트 지원
  - 자동 스케일링 전략
  - 비용 추정 ($4,500-9,200/월)

**데이터베이스 레이어 구현**:
- `apps/api/src/db/`: 비동기 데이터베이스 모듈
  - SQLAlchemy 2.0 비동기 연결 풀
  - 멀티 테넌트 스키마 (Organization, User, Workspace)
  - 감사 로그 모델 (해시만 저장)
  - 리소스 사용량 모델

**캐싱 레이어 구현**:
- `apps/api/src/services/cache_service.py`: Redis 캐싱 서비스
  - 워크스페이스 목록 캐싱 (5분 TTL)
  - 파일 트리 캐싱 (1분 TTL)
  - 패턴 기반 캐시 무효화

**서비스 레이어 분리**:
- `apps/api/src/services/workspace_service.py`: 비즈니스 로직 분리
  - 데이터베이스 연동
  - 캐시 통합
  - 워크스페이스 CRUD 작업

**의존성 추가**:
- SQLAlchemy 2.0 (비동기)
- asyncpg (PostgreSQL 비동기 드라이버)
- redis 5.0 (비동기 지원)

### 2. 컨테이너 기반 워크스페이스 설계

**문서 작성**:
- `docs/workspace-container-architecture.md`: 컨테이너 기반 워크스페이스 설계
  - Docker/Kubernetes 기반 격리
  - 워크스페이스 라이프사이클 관리
  - 보안 고려사항

### 3. 워크스페이스 선택 UI 개선

**변경사항**:
- `~/cctv-fastapi` 관련 코드 제거
- GitHub 클론 기능 추가 (`POST /api/workspaces/clone`)
- 워크스페이스 선택 UI 컴포넌트 생성 (`WorkspaceSelector.tsx`)
- 빈 워크스페이스 생성 기능

## 수정 내역 요약

### 추가된 파일
- `docs/scalability-architecture.md`: 대규모 스케일링 아키텍처 설계
- `docs/workspace-container-architecture.md`: 컨테이너 기반 워크스페이스 설계
- `apps/api/src/db/`: 데이터베이스 모듈 (connection.py, models.py)
- `apps/api/src/services/cache_service.py`: Redis 캐싱 서비스
- `apps/api/src/services/workspace_service.py`: 워크스페이스 서비스
- `apps/web/src/components/WorkspaceSelector.tsx`: 워크스페이스 선택 UI

### 수정된 파일
- `apps/api/requirements.txt`: 데이터베이스 및 캐시 의존성 추가
- `apps/api/src/main.py`: 데이터베이스 및 캐시 초기화 추가
- `apps/api/src/routers/workspaces.py`: GitHub 클론 기능 추가, dev_mode 제거
- `apps/api/src/utils/filesystem.py`: dev_mode 파라미터 제거
- `apps/api/src/routers/files.py`: dev_mode 제거
- `apps/api/src/routers/patch.py`: dev_mode 제거
- `apps/api/src/routers/ai.py`: dev_mode 제거
- `apps/web/src/app/page.tsx`: 워크스페이스 선택 UI 통합
- `apps/web/src/lib/api.ts`: GitHub 클론 API 추가
- `docs/architecture.md`: 스케일링 아키텍처 정보 추가
- `README.md`: 스케일링 정보 추가

### 주요 설계 결정

1. **Stateless API 설계**
   - 세션 저장 없음
   - 수평 확장 가능
   - 로드 밸런서 뒤에서 여러 인스턴스 실행 가능

2. **비동기 처리**
   - 모든 데이터베이스 쿼리 비동기
   - Redis 캐시 비동기
   - 성능 최적화

3. **멀티 테넌트 지원**
   - 조직(Organization) 단위 격리
   - 사용자별 권한 관리
   - 워크스페이스 소유권 관리

4. **캐싱 전략**
   - 워크스페이스 목록: 5분 TTL
   - 파일 트리: 1분 TTL
   - 쓰기 작업 시 자동 무효화

## 테스트

### 데이터베이스 연결 테스트
```bash
# PostgreSQL 실행 확인
psql -U postgres -d cursor_poc

# 테이블 생성 확인
\dt
```

### Redis 연결 테스트
```bash
# Redis 연결 확인
redis-cli ping
```

## 향후 작업

1. **관리자 대시보드 구현** ✅ (완료)
   - 인프라 서버 관리 UI
   - 서버 등록/인증
   - 워크스페이스 배치 정책 설정

### 2. 관리자 대시보드 및 인프라 서버 관리 구현

**문서 작성**:
- `docs/admin-dashboard-architecture.md`: 관리자 대시보드 및 인프라 서버 관리 아키텍처 설계
  - 서버 등록/관리 시스템
  - 인증 및 신원 증명 (SSH 키, mTLS, API 키)
  - 워크스페이스 배치 정책
  - 상용 SaaS 수준의 보안 설계

**데이터베이스 모델 추가**:
- `InfrastructureServerModel`: 인프라 서버 정보
- `ServerCredentialModel`: 서버 인증 정보 (암호화 저장)
- `WorkspacePlacementModel`: 워크스페이스 배치 정보
- `PlacementPolicyModel`: 배치 정책 설정

**인증 서비스 구현**:
- `apps/api/src/services/auth_service.py`: 인증 서비스
  - SSH 키 암호화/복호화
  - mTLS 인증서 관리
  - API 키 생성/검증
  - Fernet 기반 암호화

**관리자 API 구현**:
- `apps/api/src/routers/admin.py`: 관리자 API 라우터
  - `POST /api/admin/servers`: 서버 등록
  - `GET /api/admin/servers`: 서버 목록 조회
  - `POST /api/admin/servers/{id}/test`: 연결 테스트
  - `POST /api/admin/workspaces/{id}/place`: 워크스페이스 배치

**배치 서비스 구현**:
- `apps/api/src/services/placement_service.py`: 워크스페이스 배치 서비스
  - Least Loaded 알고리즘
  - Round Robin 알고리즘
  - Region Based 알고리즘

**관리자 대시보드 UI**:
- `apps/web/src/app/admin/`: 관리자 대시보드
  - `layout.tsx`: 관리자 레이아웃
  - `page.tsx`: 대시보드 메인 (통계 및 서버 목록)
  - `servers/page.tsx`: 서버 관리 페이지
  - `servers/new/page.tsx`: 서버 등록 페이지
- `apps/web/src/lib/admin-api.ts`: 관리자 API 클라이언트

**의존성 추가**:
- `cryptography>=41.0.0`: 암호화 라이브러리

2. **Kubernetes 통합**
   - WorkspaceManager 구현
   - Pod 생성/삭제 API
   - 리소스 모니터링

3. **자동 스케일링**
   - HPA 설정
   - 노드 자동 스케일링
   - 워크스페이스 자동 정지/재시작

4. **프로덕션 준비**
   - 부하 테스트
   - 고가용성 구성
   - 모니터링 대시보드

## 참고

- **스케일링 설계**: `docs/scalability-architecture.md`
- **컨테이너 아키텍처**: `docs/workspace-container-architecture.md`
- **아키텍처 개요**: `docs/architecture.md`
