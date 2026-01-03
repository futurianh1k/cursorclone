# 🗺️ 후속 개발 로드맵 (2026년 1월)

> 이 문서는 Claude Opus의 프로젝트 리뷰 결과를 바탕으로 작성된 후속 개발 계획입니다.

---

## 📊 현재 상태 요약

### 완성도 평가: ⭐⭐⭐⭐⭐ (5/5) - 프로덕션 배포 준비 완료

| 항목 | 상태 | 비고 |
|------|------|------|
| 오프라인 지원 | ✅ 완벽 | 외부 인터넷 불필요 |
| LLM 통합 | ✅ 탁월 | httpx + vLLM 직접 연동 |
| 보안 설계 | ✅ 완벽 | AGENTS.md 원칙 100% 준수 |
| 인증/권한 | ✅ 완료 | JWT, 2FA, Rate Limiting |
| CI/CD | ✅ 완료 | GitHub Actions |
| 테스트 | ✅ 완료 | Unit/Integration/E2E |

---

## 🚀 Phase 1: 배포 준비 (즉시 ~ 1주)

### 1.1 오프라인 배포 가이드 작성 (P0)
**목표**: 에어갭(Air-Gap) 환경 배포 문서화

```
docs/offline-deployment.md
├── 1. 사전 준비 (온라인 환경)
│   ├── Docker 이미지 다운로드 및 저장
│   ├── LLM 모델 다운로드
│   └── npm/pip 패키지 오프라인 미러
├── 2. 오프라인 서버 설정
│   ├── 이미지 로드
│   ├── 모델 캐시 복사
│   └── 서비스 실행
└── 3. 검증
    └── 외부 네트워크 차단 상태 테스트
```

**담당 파일**:
- `docs/offline-deployment.md` (신규)
- `scripts/prepare-offline.sh` (신규)
- `scripts/deploy-offline.sh` (신규)

### 1.2 에어갭 배포 스크립트 (P0)
**목표**: 원클릭 오프라인 배포 패키지 생성

```bash
# scripts/prepare-offline.sh
#!/bin/bash
# 온라인 환경에서 실행하여 오프라인 배포 패키지 생성

# 1. Docker 이미지 저장
docker save -o images.tar \
  vllm/vllm-openai:latest \
  postgres:15-alpine \
  redis:7-alpine \
  ghcr.io/cursor-onprem-poc/api:latest \
  ghcr.io/cursor-onprem-poc/web:latest

# 2. LLM 모델 다운로드
huggingface-cli download Qwen/Qwen2.5-Coder-7B-Instruct \
  --local-dir ./models/qwen2.5-coder-7b

# 3. 패키지 아카이브
tar -czf offline-deploy-$(date +%Y%m%d).tar.gz \
  images.tar \
  models/ \
  docker-compose.yml \
  docker-compose.vllm.yml \
  .env.example
```

### 1.3 GPU 환경별 모델 가이드 (P1)
**목표**: 하드웨어에 따른 최적 모델 선택 가이드

| GPU VRAM | 권장 모델 | 성능 |
|----------|-----------|------|
| 8GB | Qwen2.5-Coder-1.5B-Instruct | 기본 |
| 16GB | Qwen2.5-Coder-7B-Instruct | **권장** |
| 24GB | Qwen2.5-Coder-14B-Instruct | 고성능 |
| 40GB+ | Qwen2.5-Coder-32B-Instruct | 최고 성능 |

---

## 🔧 Phase 2: 운영 안정화 (1~2주)

### 2.1 모니터링 대시보드 구축 (P1)
**목표**: Grafana + Prometheus 기반 운영 모니터링

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:v2.48.0
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.2.0
    volumes:
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    ports:
      - "3100:3000"
```

**대시보드 항목**:
- API 요청/응답 시간
- LLM 토큰 사용량
- GPU 메모리 사용률
- 워크스페이스 활성 세션 수
- 에러율 및 알림

### 2.2 백업/복구 자동화 (P1)
**목표**: 데이터 손실 방지 체계 구축

```bash
# scripts/backup.sh
#!/bin/bash
# 일일 자동 백업 스크립트

BACKUP_DIR=/backups/$(date +%Y%m%d)
mkdir -p $BACKUP_DIR

# PostgreSQL 백업
pg_dump -h db -U cursor cursor_db > $BACKUP_DIR/db.sql

# Redis 백업
redis-cli -h redis SAVE
cp /data/redis/dump.rdb $BACKUP_DIR/

# 워크스페이스 백업 (선택적)
tar -czf $BACKUP_DIR/workspaces.tar.gz /workspaces

# 7일 이상 오래된 백업 삭제
find /backups -type d -mtime +7 -exec rm -rf {} +
```

### 2.3 로그 관리 체계 (P1)
**목표**: 중앙화된 로그 수집 및 분석

```yaml
# 이미 구현된 logging_service.py 활용
# - Elasticsearch 연동
# - Loki 연동
# - Splunk HEC 연동
```

---

## 🏢 Phase 3: 엔터프라이즈 기능 (2~4주)

### 3.1 SSO/LDAP 통합 (P2)
**목표**: 기업 인증 시스템 연동

```python
# apps/api/src/services/ldap_service.py
from ldap3 import Server, Connection, ALL

class LDAPAuthService:
    """Active Directory / LDAP 인증 서비스"""
    
    async def authenticate(self, username: str, password: str) -> User:
        # LDAP 바인딩
        # 사용자 정보 조회
        # 그룹 멤버십 확인
        pass
```

**지원 프로토콜**:
- LDAP/LDAPS (Active Directory)
- SAML 2.0 (Keycloak 활용)
- OpenID Connect

### 3.2 감사 로그 고도화 (P2)
**목표**: 금융권 규제 준수 (ISMS-P)

```python
# 이미 구현된 audit_service.py 확장
class EnhancedAuditService:
    """강화된 감사 로그 서비스"""
    
    async def log_with_retention(
        self,
        action: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        details_hash: str,  # 원문 대신 해시 저장 (보안)
        retention_years: int = 5,  # 5년 보관
    ):
        pass
```

**감사 항목**:
- 로그인/로그아웃
- AI 요청 (프롬프트 해시만 저장)
- 파일 접근/수정
- 권한 변경
- 시스템 설정 변경

### 3.3 멀티 테넌시 지원 (P2)
**목표**: 부서/팀별 격리된 환경 제공

```python
# apps/api/src/models/tenant.py
class TenantModel(Base):
    """테넌트 (조직/부서) 모델"""
    __tablename__ = "tenants"
    
    id = Column(UUID, primary_key=True)
    name = Column(String, nullable=False)
    
    # 리소스 제한
    max_workspaces = Column(Integer, default=10)
    max_users = Column(Integer, default=50)
    gpu_quota_hours = Column(Integer, default=100)
    
    # 설정
    allowed_models = Column(JSONB)  # 허용된 LLM 모델 목록
    custom_branding = Column(JSONB)  # 커스텀 로고/테마
```

---

## 🎯 Phase 4: 고급 AI 기능 (4~8주)

### 4.1 코드 RAG 시스템 (P3)
**목표**: 대규모 코드베이스 검색 및 컨텍스트 구축

```python
# apps/api/src/services/code_rag_service.py
class CodeRAGService:
    """코드 RAG (Retrieval-Augmented Generation) 서비스"""
    
    def __init__(self, vector_store: VectorStore):
        self.embedder = CodeEmbedder()  # 코드 임베딩 모델
        self.vector_store = vector_store  # Qdrant/Milvus
    
    async def index_repository(self, repo_path: str):
        """저장소 전체 인덱싱"""
        for file in self._walk_code_files(repo_path):
            chunks = self._chunk_code(file)
            embeddings = self.embedder.embed(chunks)
            await self.vector_store.upsert(chunks, embeddings)
    
    async def search_similar_code(
        self, 
        query: str, 
        top_k: int = 10
    ) -> List[CodeChunk]:
        """유사 코드 검색"""
        query_embedding = self.embedder.embed([query])[0]
        return await self.vector_store.search(query_embedding, top_k)
```

**기술 스택**:
- 벡터 DB: Qdrant (오프라인 설치 가능)
- 임베딩 모델: CodeBERT / StarEncoder
- 청킹 전략: AST 기반 함수/클래스 단위

### 4.2 자동 테스트 생성 (P3)
**목표**: AI 기반 테스트 코드 자동 생성

```python
# apps/api/src/services/test_generator.py
class TestGeneratorService:
    """AI 기반 테스트 생성 서비스"""
    
    async def generate_tests(
        self,
        source_code: str,
        language: str,
        test_framework: str,  # pytest, vitest, jest
    ) -> str:
        """소스 코드에 대한 테스트 자동 생성"""
        prompt = self._build_test_prompt(source_code, language, test_framework)
        response = await self.llm_client.chat([
            {"role": "system", "content": TEST_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])
        return self._extract_test_code(response)
```

### 4.3 코드 리뷰 자동화 (P3)
**목표**: PR/커밋에 대한 AI 리뷰 자동화

```python
# apps/api/src/services/code_review_service.py
class CodeReviewService:
    """AI 코드 리뷰 서비스"""
    
    async def review_diff(self, diff: str) -> ReviewResult:
        """Git diff에 대한 코드 리뷰"""
        return ReviewResult(
            summary="변경 요약",
            issues=[
                Issue(severity="warning", line=42, message="..."),
            ],
            suggestions=[
                Suggestion(line=50, original="...", improved="..."),
            ],
            security_concerns=[],
            performance_notes=[],
        )
```

---

## 📅 타임라인 요약

```
2026년 1월
├── Week 1: Phase 1 완료 (오프라인 배포 준비)
│   ├── docs/offline-deployment.md
│   ├── scripts/prepare-offline.sh
│   └── GPU별 모델 가이드
│
├── Week 2: Phase 2 시작 (운영 안정화)
│   ├── 모니터링 대시보드
│   └── 백업/복구 자동화
│
├── Week 3-4: Phase 3 시작 (엔터프라이즈)
│   ├── SSO/LDAP 통합
│   └── 감사 로그 고도화
│
└── Week 5+: Phase 4 (고급 AI)
    ├── 코드 RAG 시스템
    └── 자동 테스트 생성
```

---

## 🎖️ 우선순위 정의

| 등급 | 의미 | 예시 |
|------|------|------|
| **P0** | 즉시 필요 | 오프라인 배포 가이드 |
| **P1** | 배포 전 완료 | 모니터링, 백업 |
| **P2** | 1차 운영 후 | SSO, 감사 로그 |
| **P3** | 장기 로드맵 | 코드 RAG, 자동 테스트 |

---

## ✅ 체크리스트

### Phase 1 (P0-P1)
- [ ] `docs/offline-deployment.md` 작성
- [ ] `scripts/prepare-offline.sh` 작성
- [ ] `scripts/deploy-offline.sh` 작성
- [ ] GPU별 모델 가이드 업데이트
- [ ] 오프라인 배포 테스트 완료

### Phase 2 (P1)
- [ ] Prometheus 설정
- [ ] Grafana 대시보드 구축
- [ ] 백업 스크립트 작성
- [ ] 복구 테스트 완료

### Phase 3 (P2)
- [ ] LDAP 연동 구현
- [ ] SAML 2.0 연동 (Keycloak)
- [ ] 감사 로그 고도화
- [ ] 멀티 테넌시 구현

### Phase 4 (P3)
- [ ] 벡터 DB 설정 (Qdrant)
- [ ] 코드 임베딩 파이프라인
- [ ] RAG 검색 API
- [ ] 테스트 생성 기능
- [ ] 코드 리뷰 자동화

---

## 📚 참고 자료

- [Opus 프로젝트 리뷰 (2026-01-03)](./project-review-2026-01-03.md)
- [아키텍처 문서](./claudeaivdedev/docs/01-ARCHITECTURE.md)
- [보안 통제](./claudeaivdedev/docs/02-SECURITY-CONTROLS.md)
- [운영 가이드](./claudeaivdedev/docs/03-OPERATIONS-GUIDE.md)
- [로드맵](./claudeaivdedev/docs/04-ROADMAP.md)
- [PRD](./claudeaivdedev/docs/05-PRD.md)

---

*마지막 업데이트: 2026-01-03*
*작성자: Claude (Opus 리뷰 기반)*
