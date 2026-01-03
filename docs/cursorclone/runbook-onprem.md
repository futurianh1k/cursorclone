# On-Prem Runbook (PoC)

**버전**: 1.0.0  
**작성일**: 2025-12-31  
**대상**: 인프라/DevOps, 보안팀, 운영팀

---

## 목차

1. [네트워크 보안](#1-네트워크-보안)
2. [로그/감사 정책](#2-로그감사-정책)
3. [Workspace 격리](#3-workspace-격리)
4. [권한 관리 (RBAC)](#4-권한-관리-rbac)
5. [배포 절차](#5-배포-절차)
6. [모니터링 및 알림](#6-모니터링-및-알림)
7. [백업 및 복구](#7-백업-및-복구)
8. [장애 대응](#8-장애-대응)
9. [보안 점검](#9-보안-점검)
10. [GPU 노드 관리](#10-gpu-노드-관리)
11. [운영 점검 체크리스트](#11-운영-점검-체크리스트)

---

## 1. 네트워크 보안

### 1.1 인터넷 차단 정책

#### LLM 노드 (vLLM)
- **Outbound 차단**: LLM 노드는 외부 네트워크(인터넷) 접근 완전 차단
- **Inbound 허용**: 내부 API 서버에서만 접근 가능
- **포트**: 8001 (vLLM OpenAI 호환 API)

**구현 방법**:
```bash
# iptables 규칙 예시
# LLM 노드에서 실행
iptables -A OUTPUT -d 0.0.0.0/0 -j DROP
iptables -A INPUT -s <API_SERVER_IP> -p tcp --dport 8001 -j ACCEPT
iptables -A INPUT -s 127.0.0.1 -p tcp --dport 8001 -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
```

**검증**:
```bash
# LLM 노드에서 외부 접근 시도
curl -I https://www.google.com
# Connection timeout 예상
```

#### API/Web 노드
- **Inbound**: 내부망에서만 접근 가능
- **Outbound**: 
  - LLM 노드 접근 허용
  - 외부 네트워크 차단 (필요 시 허용된 내부 주소만)

**방화벽 규칙**:
```bash
# API/Web 노드
# Inbound: 내부망 IP 대역만 허용
iptables -A INPUT -s <INTERNAL_NETWORK>/24 -p tcp --dport 8000 -j ACCEPT
iptables -A INPUT -s <INTERNAL_NETWORK>/24 -p tcp --dport 3000 -j ACCEPT

# Outbound: LLM 노드만 허용
iptables -A OUTPUT -d <LLM_NODE_IP> -p tcp --dport 8001 -j ACCEPT
```

### 1.2 mTLS 적용 (선택사항)

**필요 시나리오**:
- 높은 보안 요구사항
- 다중 데이터센터 간 통신
- 규제 준수 요구

**구현**:
```bash
# 인증서 생성 (예: cert-manager 사용)
kubectl apply -f cert-manager.yaml

# mTLS 설정 (예: Istio)
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
spec:
  mtls:
    mode: STRICT
```

### 1.3 네트워크 분리 (권장)

```
┌─────────────────────────────────────────┐
│         내부망 (Internal Network)        │
│                                         │
│  ┌──────────┐      ┌──────────┐       │
│  │   Web    │──────▶│   API    │       │
│  │ (Next.js)│      │(FastAPI) │       │
│  └──────────┘      └─────┬─────┘       │
│                          │             │
│                          ▼             │
│                    ┌──────────┐        │
│                    │   vLLM   │        │
│                    │  (GPU)   │        │
│                    └──────────┘        │
│                                         │
│  [인터넷 차단]                          │
└─────────────────────────────────────────┘
```

---

## 2. 로그/감사 정책

### 2.1 원문 저장 금지 원칙

**⚠️ 중요**: 프롬프트/응답 원문은 절대 저장하지 않습니다.

**금지 항목**:
- ❌ 프롬프트 원문
- ❌ LLM 응답 원문
- ❌ 코드 선택 내용 원문
- ❌ 사용자 지시사항 원문

**허용 항목**:
- ✅ SHA-256 해시
- ✅ 메타데이터 (user_id, workspace_id, action, timestamp)
- ✅ 파일 경로 (내용 제외)
- ✅ 토큰 사용량
- ✅ 응답 시간

### 2.2 감사 로그 스키마

**PostgreSQL 테이블 예시**:
```sql
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- 사용자/워크스페이스
    user_id VARCHAR(100) NOT NULL,
    workspace_id VARCHAR(100) NOT NULL,
    
    -- 액션 정보
    action VARCHAR(50) NOT NULL,  -- 'explain', 'rewrite', 'patch_apply'
    source_count INTEGER,
    source_paths TEXT[],  -- 파일 경로만 (내용 X)
    
    -- 해시 (검증용)
    instruction_hash VARCHAR(64),  -- SHA-256
    context_hash VARCHAR(64),      -- SHA-256
    response_hash VARCHAR(64),     -- SHA-256
    patch_hash VARCHAR(64),        -- SHA-256 (patch_apply인 경우)
    
    -- 성능 메트릭
    tokens_estimated INTEGER,
    tokens_used INTEGER,
    latency_ms INTEGER,
    
    -- 기타
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_workspace_id ON audit_logs(workspace_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
```

### 2.3 로그 저장 예시

**Python 코드 예시**:
```python
import hashlib
from datetime import datetime

def create_audit_log(
    user_id: str,
    workspace_id: str,
    action: str,
    instruction: str,
    context_messages: List[str],
    response: str,
    patch: Optional[str] = None,
) -> dict:
    """감사 로그 생성 (원문 저장 금지)"""
    
    # 해시 생성
    instruction_hash = hashlib.sha256(instruction.encode()).hexdigest()
    context_hash = hashlib.sha256("\n".join(context_messages).encode()).hexdigest()
    response_hash = hashlib.sha256(response.encode()).hexdigest()
    
    log = {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "action": action,
        "instruction_hash": instruction_hash,
        "context_hash": context_hash,
        "response_hash": response_hash,
        "timestamp": datetime.utcnow(),
    }
    
    if patch:
        log["patch_hash"] = hashlib.sha256(patch.encode()).hexdigest()
    
    return log
```

### 2.4 로그 보관 정책

- **보관 기간**: 최소 1년 (규제 요구사항에 따라 조정)
- **백업**: 일일 백업 (암호화)
- **접근 제어**: 감사팀만 읽기 권한
- **삭제 정책**: 보관 기간 경과 후 자동 삭제 (또는 아카이브)

---

## 3. Workspace 격리

### 3.1 파일시스템 격리

**디렉토리 구조**:
```
/workspaces/
├── ws_user1_project1/
│   ├── src/
│   ├── README.md
│   └── ...
├── ws_user2_project2/
│   ├── src/
│   └── ...
└── ...
```

**권한 설정**:
```bash
# 워크스페이스 생성 시
WORKSPACE_ROOT="/workspaces/ws_${workspace_id}"
mkdir -p "$WORKSPACE_ROOT"
chown ${user_id}:${user_id} "$WORKSPACE_ROOT"
chmod 700 "$WORKSPACE_ROOT"  # 소유자만 접근 가능
```

### 3.2 경로 검증

**보안 필터 검증 항목**:
1. 절대 경로 금지 (`/`로 시작)
2. 경로 탈출 방지 (`../`, `..\\`)
3. 심볼릭 링크 검증
4. 워크스페이스 루트 내 경로인지 확인

**구현 위치**: `apps/api/src/context_builder/security.py`

### 3.3 컨테이너 격리 (선택사항)

**Docker/Kubernetes 사용 시**:
```yaml
# Kubernetes 예시
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  volumes:
    - name: workspace
      persistentVolumeClaim:
        claimName: workspace-${workspace_id}
```

---

## 4. 권한 관리 (RBAC)

### 4.1 기본 권한

**사용자 역할**:
- **Developer**: 기본 사용자
  - 워크스페이스 생성/조회
  - 파일 읽기/쓰기
  - AI Explain (코드 설명)
  - ❌ AI Rewrite (코드 수정) - 기본 Off
  - ❌ Patch Apply (코드 변경 적용) - 기본 Off

- **AI-Developer**: AI 수정 권한 보유
  - Developer 권한 + AI Rewrite + Patch Apply

- **Admin**: 관리자
  - 모든 권한
  - 워크스페이스 관리
  - 사용자 관리

### 4.2 AI-Modify 권한 분리

**권한 체크 예시**:
```python
# apps/api/src/routers/ai.py
async def rewrite_code(request: AIRewriteRequest, current_user: User):
    # AI-Modify 권한 확인
    if not current_user.has_permission("ai_modify"):
        raise HTTPException(
            status_code=403,
            detail={"error": "AI-Modify permission required", "code": "PERMISSION_DENIED"}
        )
    # ...
```

**권한 테이블 예시**:
```sql
CREATE TABLE user_permissions (
    user_id VARCHAR(100) NOT NULL,
    permission VARCHAR(50) NOT NULL,  -- 'ai_modify', 'workspace_admin', etc.
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    granted_by VARCHAR(100),
    PRIMARY KEY (user_id, permission)
);

-- 기본 권한 부여 (AI-Modify는 별도 승인 필요)
INSERT INTO user_permissions (user_id, permission) VALUES
    ('user1', 'workspace_read'),
    ('user1', 'workspace_write'),
    ('user1', 'ai_explain');
-- 'ai_modify'는 관리자가 별도로 부여
```

### 4.3 권한 승인 프로세스

1. **요청**: 사용자가 AI-Modify 권한 요청
2. **검토**: 관리자 검토 (보안팀 협의)
3. **승인/거부**: 관리자 승인 또는 거부
4. **감사 로그**: 권한 부여/회수 기록

---

## 5. 배포 절차

### 5.1 사전 준비

**체크리스트**:
- [ ] 네트워크 설정 완료 (방화벽 규칙)
- [ ] GPU 노드 준비 (vLLM용)
- [ ] PostgreSQL DB 준비 (감사 로그용)
- [ ] 인증서 준비 (mTLS 사용 시)
- [ ] 환경 변수 설정 파일 준비

### 5.2 환경 변수 설정

**.env 파일 예시**:
```bash
# API 서버
API_HOST=0.0.0.0
API_PORT=8000
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://internal.company.local

# vLLM
VLLM_BASE_URL=http://vllm-node:8001/v1
VLLM_API_KEY=dummy-key

# 데이터베이스
DATABASE_URL=postgresql://user:password@db-host:5432/audit_db

# 워크스페이스
WORKSPACE_ROOT=/workspaces

# 보안
ALLOWED_EXTENSIONS=.py,.js,.ts,.tsx,.jsx,.java,.go,.rs,.c,.cpp,.h,.rb,.php,.swift,.kt,.scala,.cs,.sql,.sh,.bash,.yaml,.yml,.json,.md,.txt,.html,.css,.xml,.dockerfile,.gitignore,.env
MAX_FILE_SIZE=10485760  # 10MB
MAX_PATCH_SIZE=1048576   # 1MB
```

### 5.3 배포 단계

**1. vLLM 배포**:
```bash
cd infra/llm
docker-compose -f vllm-compose.yml up -d

# 확인
curl http://localhost:8001/health
```

**2. API 서버 배포**:
```bash
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # 또는 pyproject.toml 기반 설치

# 환경 변수 로드
export $(cat .env | xargs)

# 실행
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

**3. Web 서버 배포**:
```bash
cd apps/web
pnpm install
pnpm build
pnpm start
```

**4. 검증**:
```bash
# Health check
curl http://localhost:8000/health

# API 문서 확인
open http://localhost:8000/docs
```

### 5.4 Kubernetes 배포 (선택사항)

**Deployment 예시**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cursor-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cursor-api
  template:
    metadata:
      labels:
        app: cursor-api
    spec:
      containers:
      - name: api
        image: cursor-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: VLLM_BASE_URL
          value: "http://vllm-service:8001/v1"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

---

## 6. 모니터링 및 알림

### 6.1 모니터링 지표

**시스템 메트릭**:
- CPU 사용률
- 메모리 사용률
- 디스크 사용률
- 네트워크 트래픽

**애플리케이션 메트릭**:
- API 요청 수 (QPS)
- API 응답 시간 (latency)
- 에러율 (4xx, 5xx)
- LLM 응답 시간
- 토큰 사용량

**비즈니스 메트릭**:
- 활성 사용자 수
- 워크스페이스 수
- AI 요청 수 (explain/rewrite)
- 패치 적용 수

### 6.2 알림 설정

**Prometheus + Grafana 예시**:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'cursor-api'
    static_configs:
      - targets: ['api:8000']
```

**알림 규칙**:
- LLM 서비스 다운 (5분 이상)
- API 에러율 > 5% (5분 평균)
- 디스크 사용률 > 80%
- 메모리 사용률 > 90%

### 6.3 로그 수집

**ELK Stack 또는 Loki 사용**:
```yaml
# 로그 수집 설정
logging:
  level: INFO
  format: json
  output: stdout
```

**중요 로그**:
- 보안 이벤트 (경로 탈출 시도, 권한 위반)
- 에러 로그 (5xx)
- 감사 로그 (해시만)

---

## 7. 백업 및 복구

### 7.1 백업 대상

**데이터베이스**:
- 감사 로그 (PostgreSQL)
- 사용자 권한
- 워크스페이스 메타데이터

**파일시스템**:
- 워크스페이스 파일 (`/workspaces/*`)
- 설정 파일
- 인증서

### 7.2 백업 절차

**일일 백업 스크립트 예시**:
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backup/${DATE}"

mkdir -p "$BACKUP_DIR"

# PostgreSQL 백업
pg_dump -U postgres audit_db > "$BACKUP_DIR/audit_db.sql"

# 워크스페이스 백업
tar -czf "$BACKUP_DIR/workspaces.tar.gz" /workspaces/

# 설정 파일 백업
cp -r /etc/cursor-onprem "$BACKUP_DIR/config"

# 암호화 (선택사항)
gpg --encrypt --recipient backup@company.com "$BACKUP_DIR/audit_db.sql"
```

**Cron 설정**:
```bash
# 매일 새벽 2시 백업
0 2 * * * /usr/local/bin/backup.sh
```

### 7.3 복구 절차

**데이터베이스 복구**:
```bash
# 백업 파일에서 복구
psql -U postgres audit_db < /backup/20251231/audit_db.sql
```

**워크스페이스 복구**:
```bash
# 압축 해제
tar -xzf /backup/20251231/workspaces.tar.gz -C /
```

---

## 8. 장애 대응

### 8.1 장애 유형별 대응

#### LLM 서비스 다운
**증상**: `/api/ai/*` 엔드포인트 503 에러

**대응**:
1. vLLM 서비스 상태 확인
   ```bash
   curl http://vllm-node:8001/health
   ```
2. GPU 노드 상태 확인
   ```bash
   nvidia-smi
   ```
3. 로그 확인
   ```bash
   docker logs vllm-container
   ```
4. 재시작
   ```bash
   docker-compose -f vllm-compose.yml restart
   ```

#### API 서버 다운
**증상**: 모든 API 엔드포인트 응답 없음

**대응**:
1. 프로세스 확인
   ```bash
   ps aux | grep uvicorn
   ```
2. 포트 확인
   ```bash
   netstat -tlnp | grep 8000
   ```
3. 로그 확인
   ```bash
   tail -f /var/log/cursor-api/error.log
   ```
4. 재시작
   ```bash
   systemctl restart cursor-api
   ```

#### 데이터베이스 다운
**증상**: 감사 로그 저장 실패

**대응**:
1. PostgreSQL 상태 확인
   ```bash
   systemctl status postgresql
   ```
2. 연결 확인
   ```bash
   psql -U postgres -c "SELECT 1"
   ```
3. 디스크 공간 확인
   ```bash
   df -h
   ```

### 8.2 장애 대응 체크리스트

- [ ] 장애 유형 식별
- [ ] 영향 범위 파악
- [ ] 로그 확인
- [ ] 임시 조치 (재시작 등)
- [ ] 근본 원인 분석
- [ ] 장애 보고서 작성
- [ ] 재발 방지 대책 수립

---

## 9. 보안 점검

### 9.1 정기 점검 항목

**주간 점검**:
- [ ] 방화벽 규칙 검증
- [ ] 로그 이상 패턴 확인
- [ ] 권한 변경 이력 검토
- [ ] 보안 패치 적용 여부 확인

**월간 점검**:
- [ ] 사용자 권한 재검토
- [ ] 워크스페이스 접근 로그 분석
- [ ] 보안 취약점 스캔
- [ ] 백업 무결성 확인

**분기별 점검**:
- [ ] 전체 보안 감사
- [ ] 권한 관리 정책 검토
- [ ] 재해 복구 훈련
- [ ] 보안 교육 실시

### 9.2 보안 점검 체크리스트

**네트워크 보안**:
- [ ] LLM 노드 outbound 차단 확인
- [ ] API/Web 노드 접근 제어 확인
- [ ] 방화벽 규칙 검증
- [ ] mTLS 인증서 유효성 확인

**애플리케이션 보안**:
- [ ] 경로 탈출 방지 검증
- [ ] 파일 확장자 allowlist 확인
- [ ] 입력 검증 테스트
- [ ] 인증/인가 로직 검증

**데이터 보안**:
- [ ] 원문 저장 금지 확인 (해시만 저장)
- [ ] 감사 로그 무결성 확인
- [ ] 워크스페이스 격리 확인
- [ ] 백업 암호화 확인

**운영 보안**:
- [ ] 로그 접근 제어 확인
- [ ] 권한 관리 프로세스 검증
- [ ] 보안 패치 적용 확인
- [ ] 비상 계획 검토

---

## 10. GPU 노드 관리

### 10.1 GPU 모니터링

**nvidia-smi 사용**:
```bash
# GPU 상태 확인
nvidia-smi

# 지속 모니터링
watch -n 1 nvidia-smi
```

**메트릭 수집**:
```bash
# Prometheus exporter 사용
docker run -d --gpus all \
  -p 9400:9400 \
  nvidia/dcgm-exporter
```

### 10.2 GPU 리소스 관리

**vLLM 설정**:
```yaml
# vllm-compose.yml
services:
  vllm:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=0  # 특정 GPU만 사용
      - CUDA_VISIBLE_DEVICES=0
```

**GPU 할당 전략**:
- 단일 GPU: 소규모 모델 (7B 이하)
- 다중 GPU: 대규모 모델 (13B 이상)
- GPU 공유: 여러 사용자 요청 큐잉

### 10.3 GPU 노드 유지보수

**재시작 절차**:
1. 요청 큐잉 중지
2. 진행 중인 요청 완료 대기
3. vLLM 서비스 중지
4. GPU 드라이버 재시작 (필요 시)
5. vLLM 서비스 재시작
6. 헬스 체크 확인

---

## 11. 운영 점검 체크리스트

### 11.1 일일 점검

**시작 전**:
- [ ] 시스템 상태 확인 (CPU, 메모리, 디스크)
- [ ] 서비스 상태 확인 (API, Web, vLLM)
- [ ] 로그 이상 패턴 확인
- [ ] 네트워크 연결 확인

**운영 중**:
- [ ] 에러율 모니터링
- [ ] 응답 시간 모니터링
- [ ] 리소스 사용률 모니터링
- [ ] 사용자 문의 대응

**종료 전**:
- [ ] 일일 통계 확인
- [ ] 중요 이벤트 로그 검토
- [ ] 백업 완료 확인

### 11.2 주간 점검

- [ ] 성능 메트릭 분석
- [ ] 사용자 피드백 검토
- [ ] 보안 이벤트 검토
- [ ] 리소스 사용량 트렌드 분석
- [ ] 다음 주 계획 수립

### 11.3 월간 점검

- [ ] 전체 시스템 성능 평가
- [ ] 비용 분석 (GPU, 스토리지)
- [ ] 사용자 만족도 조사
- [ ] 보안 감사
- [ ] 개선 사항 도출

---

## 부록

### A. 유용한 명령어

```bash
# 서비스 상태 확인
systemctl status cursor-api
docker ps | grep vllm

# 로그 확인
tail -f /var/log/cursor-api/access.log
docker logs -f vllm-container

# 네트워크 확인
netstat -tlnp | grep 8000
iptables -L -n

# 디스크 사용량
df -h
du -sh /workspaces/*

# GPU 상태
nvidia-smi
```

### B. 연락처

- **인프라팀**: infra@company.com
- **보안팀**: security@company.com
- **운영팀**: ops@company.com
- **비상 연락**: oncall@company.com

### C. 참고 문서

- **아키텍처**: `docs/architecture.md`
- **API 명세**: `docs/api-spec.md`
- **Context Builder**: `docs/context-builder.md`
- **AGENTS 규칙**: `AGENTS.md`

---

**최종 업데이트**: 2025-12-31  
**다음 검토 예정일**: 2026-01-31
