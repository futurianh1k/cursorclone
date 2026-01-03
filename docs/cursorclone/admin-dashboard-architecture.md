# 관리자 대시보드 및 인프라 서버 관리 아키텍처

**작성일**: 2025-01-02  
**목적**: 상용 SaaS 수준의 인프라 관리 시스템  
**상태**: 설계 단계

---

## 1. 개요

관리자 대시보드는 인프라 서버를 등록하고 관리하며, 워크스페이스 컨테이너를 배치할 서버를 선택할 수 있는 시스템입니다.

### 주요 기능

1. **인프라 서버 관리**
   - 서버 등록/수정/삭제
   - 서버 상태 모니터링
   - 연결 테스트

2. **인증 및 신원 증명**
   - SSH 키 기반 인증
   - mTLS 인증
   - API 키 인증
   - 자격 증명 암호화 저장

3. **워크스페이스 배치 정책**
   - 서버 선택 알고리즘
   - 리소스 기반 배치
   - 지역/존 기반 배치
   - 부하 분산

4. **모니터링 및 알림**
   - 서버 리소스 사용량
   - 워크스페이스 분포
   - 장애 알림

---

## 2. 아키텍처 설계

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────┐
│              관리자 대시보드 (Admin Dashboard)            │
│  - 서버 관리 UI                                          │
│  - 워크스페이스 배치 정책 설정                           │
│  - 모니터링 대시보드                                     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/WebSocket
                       ▼
┌─────────────────────────────────────────────────────────┐
│              API 서버 (FastAPI)                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  인프라 서버 관리 API                              │  │
│  │  - POST /api/admin/servers                       │  │
│  │  - GET /api/admin/servers                        │  │
│  │  - POST /api/admin/servers/{id}/test             │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  인증 관리 서비스                                  │  │
│  │  - SSH 키 관리                                    │  │
│  │  - mTLS 인증서 관리                               │  │
│  │  - API 키 생성/회전                               │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  워크스페이스 배치 서비스                          │  │
│  │  - 서버 선택 알고리즘                              │  │
│  │  - 리소스 확인                                     │  │
│  │  - 배치 실행                                       │  │
│  └──────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Server 1    │ │  Server 2    │ │  Server 3    │
│  (K8s)       │ │  (K8s)       │ │  (Docker)    │
│              │ │              │ │              │
│  - ws_001    │ │  - ws_002    │ │  - ws_003    │
│  - ws_004    │ │  - ws_005    │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 2.2 데이터베이스 스키마

```sql
-- 인프라 서버 테이블
CREATE TABLE infrastructure_servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 22,
    type VARCHAR(50) NOT NULL, -- kubernetes, docker, ssh
    region VARCHAR(100),
    zone VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, inactive, maintenance
    max_workspaces INTEGER DEFAULT 100,
    current_workspaces INTEGER DEFAULT 0,
    cpu_capacity DECIMAL(10,2), -- 총 CPU cores
    memory_capacity BIGINT, -- 총 메모리 (bytes)
    disk_capacity BIGINT, -- 총 디스크 (bytes)
    cpu_usage DECIMAL(10,2) DEFAULT 0,
    memory_usage BIGINT DEFAULT 0,
    disk_usage BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_health_check TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_region (region)
);

-- 서버 인증 정보 (암호화 저장)
CREATE TABLE server_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    server_id UUID NOT NULL REFERENCES infrastructure_servers(id) ON DELETE CASCADE,
    auth_type VARCHAR(50) NOT NULL, -- ssh_key, mtls, api_key
    credential_name VARCHAR(255) NOT NULL,
    -- 암호화된 필드들
    encrypted_private_key TEXT, -- SSH private key 또는 mTLS key (암호화)
    encrypted_certificate TEXT, -- mTLS certificate (암호화)
    encrypted_api_key TEXT, -- API key (암호화)
    public_key TEXT, -- SSH public key (평문 가능)
    -- 메타데이터
    key_fingerprint VARCHAR(64), -- SSH 키 지문
    expires_at TIMESTAMP, -- 인증서 만료일
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(server_id, auth_type, credential_name)
);

-- 워크스페이스 배치 정보
CREATE TABLE workspace_placements (
    workspace_id VARCHAR(100) PRIMARY KEY REFERENCES workspaces(workspace_id),
    server_id UUID NOT NULL REFERENCES infrastructure_servers(id),
    container_id VARCHAR(255), -- Pod 이름 또는 컨테이너 ID
    placement_policy VARCHAR(50), -- auto, manual, region_based
    placed_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_server_id (server_id)
);

-- 배치 정책 설정
CREATE TABLE placement_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    policy_type VARCHAR(50) NOT NULL, -- round_robin, least_loaded, region_based
    enabled BOOLEAN DEFAULT true,
    config JSONB, -- 정책별 설정 (예: 지역 우선순위, 리소스 가중치)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 3. 인증 시스템 설계

### 3.1 SSH 키 기반 인증

**특징**:
- 가장 일반적인 서버 접근 방식
- 공개키/비공개키 쌍 사용
- 비공개키는 암호화하여 저장

**구현**:
```python
# apps/api/src/services/auth_service.py

from cryptography.fernet import Fernet
import base64
import hashlib

class SSHAuthService:
    """SSH 키 기반 인증 서비스"""
    
    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)
    
    def encrypt_private_key(self, private_key: str) -> str:
        """SSH 비공개키 암호화"""
        return self.cipher.encrypt(private_key.encode()).decode()
    
    def decrypt_private_key(self, encrypted_key: str) -> str:
        """SSH 비공개키 복호화"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()
    
    def get_key_fingerprint(self, public_key: str) -> str:
        """SSH 공개키 지문 생성"""
        # SSH 공개키에서 키 부분 추출
        key_part = public_key.split()[1] if len(public_key.split()) > 1 else public_key
        key_bytes = base64.b64decode(key_part)
        return hashlib.sha256(key_bytes).hexdigest()
```

### 3.2 mTLS 인증

**특징**:
- 상호 TLS 인증
- 높은 보안 수준
- 인증서 기반

**구현**:
```python
class mTLSAuthService:
    """mTLS 인증 서비스"""
    
    def encrypt_certificate(self, cert: str, key: str) -> tuple[str, str]:
        """인증서 및 키 암호화"""
        encrypted_cert = self.cipher.encrypt(cert.encode()).decode()
        encrypted_key = self.cipher.encrypt(key.encode()).decode()
        return encrypted_cert, encrypted_key
    
    def validate_certificate(self, cert: str) -> dict:
        """인증서 유효성 검증"""
        # 인증서 만료일 확인
        # CN, SAN 확인
        # 서명 검증
        pass
```

### 3.3 API 키 인증

**특징**:
- 간단한 인증 방식
- Kubernetes API 서버 접근 등에 사용
- 키 회전 지원

**구현**:
```python
class APIKeyAuthService:
    """API 키 인증 서비스"""
    
    def generate_api_key(self) -> tuple[str, str]:
        """API 키 생성 (키, 해시)"""
        import secrets
        key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, key_hash
    
    def verify_api_key(self, key: str, key_hash: str) -> bool:
        """API 키 검증"""
        return hashlib.sha256(key.encode()).hexdigest() == key_hash
```

### 3.4 자격 증명 암호화

**암호화 키 관리**:
- 환경변수에서 마스터 키 로드
- KMS 통합 (선택사항)
- 키 회전 정책

```python
# 마스터 키는 환경변수에서 로드
MASTER_ENCRYPTION_KEY = os.getenv("MASTER_ENCRYPTION_KEY")
if not MASTER_ENCRYPTION_KEY:
    # 개발 환경: 자동 생성 (프로덕션에서는 반드시 설정)
    from cryptography.fernet import Fernet
    MASTER_ENCRYPTION_KEY = Fernet.generate_key().decode()
```

---

## 4. 서버 관리 API 설계

### 4.1 서버 등록 API

```python
@router.post("/api/admin/servers")
async def register_server(
    request: RegisterServerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_admin_user),
):
    """
    인프라 서버 등록
    
    요청:
    {
        "name": "k8s-cluster-1",
        "host": "k8s.example.com",
        "port": 6443,
        "type": "kubernetes",
        "region": "us-west-1",
        "zone": "us-west-1a",
        "auth": {
            "type": "api_key",
            "api_key": "...",
            "kubeconfig": "..." // 암호화하여 저장
        }
    }
    """
    # 1. 인증 정보 암호화
    # 2. 서버 정보 저장
    # 3. 연결 테스트
    # 4. 리소스 정보 수집
    pass
```

### 4.2 서버 연결 테스트 API

```python
@router.post("/api/admin/servers/{server_id}/test")
async def test_server_connection(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    서버 연결 테스트
    
    - SSH 연결 테스트
    - Kubernetes API 연결 테스트
    - 리소스 정보 수집
    """
    pass
```

### 4.3 워크스페이스 배치 API

```python
@router.post("/api/admin/workspaces/{workspace_id}/place")
async def place_workspace(
    workspace_id: str,
    request: PlacementRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    워크스페이스 배치
    
    요청:
    {
        "server_id": "uuid", // 선택사항 (없으면 자동 선택)
        "policy": "least_loaded" // 배치 정책
    }
    """
    # 1. 서버 선택 (정책 기반)
    # 2. 리소스 확인
    # 3. 워크스페이스 배치
    # 4. 배치 정보 저장
    pass
```

---

## 5. 워크스페이스 배치 알고리즘

### 5.1 Least Loaded (기본)

```python
async def select_server_least_loaded(
    db: AsyncSession,
    region: Optional[str] = None,
) -> InfrastructureServerModel:
    """가장 적은 부하를 가진 서버 선택"""
    query = select(InfrastructureServerModel).where(
        InfrastructureServerModel.status == "active"
    )
    
    if region:
        query = query.where(InfrastructureServerModel.region == region)
    
    servers = await db.execute(query)
    servers_list = servers.scalars().all()
    
    # CPU 사용률 기준으로 정렬
    servers_list.sort(key=lambda s: s.cpu_usage / s.cpu_capacity if s.cpu_capacity else 1.0)
    
    return servers_list[0] if servers_list else None
```

### 5.2 Round Robin

```python
async def select_server_round_robin(
    db: AsyncSession,
    region: Optional[str] = None,
) -> InfrastructureServerModel:
    """라운드 로빈 방식으로 서버 선택"""
    # 마지막 배치 서버 ID를 Redis에서 가져옴
    last_server_id = await cache_service.get("placement:last_server_id")
    # 다음 서버 선택
    pass
```

### 5.3 Region Based

```python
async def select_server_region_based(
    db: AsyncSession,
    user_region: str,
) -> InfrastructureServerModel:
    """사용자 지역 기반 서버 선택"""
    # 같은 지역의 서버 우선 선택
    # 없으면 가장 가까운 지역 선택
    pass
```

---

## 6. 관리자 대시보드 UI

### 6.1 주요 화면

1. **서버 관리 화면**
   - 서버 목록 (테이블)
   - 서버 추가/수정/삭제
   - 연결 테스트 버튼
   - 리소스 사용량 차트

2. **인증 관리 화면**
   - SSH 키 관리
   - mTLS 인증서 관리
   - API 키 생성/회전

3. **워크스페이스 배치 화면**
   - 배치 정책 설정
   - 수동 배치
   - 배치 히스토리

4. **모니터링 대시보드**
   - 서버 리소스 사용량
   - 워크스페이스 분포
   - 장애 알림

### 6.2 컴포넌트 구조

```
apps/web/src/app/admin/
├── layout.tsx (관리자 레이아웃)
├── servers/
│   ├── page.tsx (서버 목록)
│   ├── [id]/page.tsx (서버 상세)
│   └── new/page.tsx (서버 등록)
├── auth/
│   ├── page.tsx (인증 관리)
│   └── ssh-keys/page.tsx (SSH 키 관리)
├── placement/
│   ├── page.tsx (배치 정책)
│   └── policies/page.tsx (정책 설정)
└── dashboard/
    └── page.tsx (모니터링 대시보드)
```

---

## 7. 보안 고려사항

### 7.1 자격 증명 보안

1. **암호화 저장**
   - 모든 민감 정보는 암호화하여 저장
   - 마스터 키는 환경변수 또는 KMS에서 관리

2. **접근 제어**
   - 관리자만 서버 등록/수정 가능
   - RBAC 기반 권한 관리

3. **감사 로그**
   - 모든 서버 접근 기록
   - 자격 증명 변경 기록

### 7.2 네트워크 보안

1. **연결 검증**
   - 서버 등록 시 연결 테스트 필수
   - 정기적인 헬스 체크

2. **격리**
   - 서버 간 네트워크 격리
   - 워크스페이스 간 격리

---

## 8. 구현 단계

### Phase 1: 데이터베이스 및 모델 (현재)
- [x] 인프라 서버 스키마 설계
- [ ] 서버 인증 정보 스키마 설계
- [ ] 배치 정책 스키마 설계

### Phase 2: 인증 서비스
- [ ] SSH 키 암호화/복호화 서비스
- [ ] mTLS 인증서 관리 서비스
- [ ] API 키 생성/검증 서비스

### Phase 3: 서버 관리 API
- [ ] 서버 등록 API
- [ ] 서버 조회/수정/삭제 API
- [ ] 연결 테스트 API

### Phase 4: 배치 서비스
- [ ] 서버 선택 알고리즘 구현
- [ ] 워크스페이스 배치 API
- [ ] 배치 정책 관리 API

### Phase 5: 관리자 대시보드
- [ ] 서버 관리 UI
- [ ] 인증 관리 UI
- [ ] 모니터링 대시보드

---

## 9. 참고 자료

- **Kubernetes Authentication**: https://kubernetes.io/docs/reference/access-authn-authz/authentication/
- **SSH Key Management**: https://www.ssh.com/academy/ssh/key
- **mTLS Guide**: https://www.cloudflare.com/learning/access-management/what-is-mutual-tls/
- **Fernet Encryption**: https://cryptography.io/en/latest/fernet/
