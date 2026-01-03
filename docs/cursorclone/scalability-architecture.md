# 대규모 스케일링 아키텍처 설계

**작성일**: 2025-01-02  
**목표 규모**: 500명 동시 사용자  
**상태**: 설계 단계

---

## 1. 요구사항 분석

### 1.1 규모 추정

**500명 조직 기준**:
- 동시 활성 워크스페이스: ~100-200개 (20-40% 활성률)
- 피크 시간대: ~300개 워크스페이스
- 워크스페이스당 평균 리소스:
  - CPU: 1-2 cores
  - Memory: 2-4 GB
  - Storage: 10-50 GB

**총 리소스 요구사항**:
- CPU: 300-600 cores
- Memory: 600 GB - 1.2 TB
- Storage: 3-15 TB

### 1.2 주요 요구사항

1. **고가용성**
   - 99.9% 이상 가동률
   - 무중단 배포
   - 장애 자동 복구

2. **자동 스케일링**
   - 워크스페이스 수에 따른 동적 확장
   - 리소스 사용량 기반 스케일링
   - 비용 최적화

3. **멀티 테넌트**
   - 조직/팀별 격리
   - 리소스 할당량 관리
   - 권한 관리

4. **성능**
   - API 응답 시간 < 200ms (p95)
   - 파일 읽기/쓰기 < 100ms
   - LLM 응답 스트리밍

5. **보안**
   - 워크스페이스 간 완전 격리
   - 네트워크 격리
   - 감사 로그

---

## 2. 아키텍처 설계

### 2.1 전체 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer                             │
│                      (Nginx / Traefik)                           │
└──────────────────────┬────────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  API Pod 1   │ │  API Pod 2   │ │  API Pod 3   │
│  (FastAPI)   │ │  (FastAPI)   │ │  (FastAPI)   │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Redis      │ │ PostgreSQL   │ │   RabbitMQ   │
│  (Cache)     │ │   (DB)       │ │  (Queue)     │
└──────────────┘ └──────────────┘ └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────┐
        │    Kubernetes Cluster            │
        │                                  │
        │  ┌────────────────────────────┐ │
        │  │  Workspace Namespace        │ │
        │  │  ┌──────┐ ┌──────┐ ┌──────┐│ │
        │  │  │ Pod  │ │ Pod  │ │ Pod  ││ │
        │  │  │ws_001│ │ws_002│ │ws_003││ │
        │  │  └──────┘ └──────┘ └──────┘│ │
        │  └────────────────────────────┘ │
        │                                  │
        │  ┌────────────────────────────┐ │
        │  │  Node Pool (Auto-scaling)  │ │
        │  │  - CPU/Memory 기반 확장    │ │
        │  │  - Spot 인스턴스 활용      │ │
        │  └────────────────────────────┘ │
        └──────────────────────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────┐
        │      vLLM Service (GPU)          │
        │  ┌──────────┐ ┌──────────┐      │
        │  │ vLLM Pod │ │ vLLM Pod │      │
        │  └──────────┘ └──────────┘      │
        └──────────────────────────────────┘
```

### 2.2 컴포넌트 상세

#### 2.2.1 API 서버 (Stateless)

**특징**:
- Stateless 설계 (세션 저장 안 함)
- 수평 확장 가능
- Kubernetes Deployment로 관리

**구성**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
spec:
  replicas: 3  # 최소 3개, HPA로 자동 확장
  template:
    spec:
      containers:
      - name: api
        image: cursor-api:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

**스케일링 전략**:
- HPA (Horizontal Pod Autoscaler): CPU/메모리 기반
- VPA (Vertical Pod Autoscaler): 리소스 최적화
- 예상: 3-10개 Pod (트래픽에 따라)

#### 2.2.2 데이터베이스 (PostgreSQL)

**요구사항**:
- 워크스페이스 메타데이터
- 사용자 정보
- 감사 로그
- 권한 정보

**구성**:
- Primary-Replica 구성 (고가용성)
- Connection Pooling (PgBouncer)
- 백업: 일일 자동 백업

**스키마 예시**:
```sql
-- 워크스페이스 테이블
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    owner_id VARCHAR(100) NOT NULL,
    org_id VARCHAR(100),
    container_id VARCHAR(255),
    status VARCHAR(50) NOT NULL, -- running, stopped, deleted
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_owner_id (owner_id),
    INDEX idx_org_id (org_id),
    INDEX idx_status (status)
);

-- 워크스페이스 리소스 사용량
CREATE TABLE workspace_resources (
    workspace_id VARCHAR(100) PRIMARY KEY,
    cpu_usage DECIMAL(10,2),
    memory_usage BIGINT, -- bytes
    disk_usage BIGINT, -- bytes
    network_io BIGINT, -- bytes
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 감사 로그 (해시만 저장)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    workspace_id VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    instruction_hash VARCHAR(64),
    response_hash VARCHAR(64),
    patch_hash VARCHAR(64),
    tokens_used INTEGER,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_id (user_id),
    INDEX idx_workspace_id (workspace_id),
    INDEX idx_timestamp (timestamp)
);
```

#### 2.2.3 캐시 (Redis)

**용도**:
- 워크스페이스 목록 캐싱
- 파일 트리 캐싱
- 세션 정보 (선택사항)
- Rate limiting

**구성**:
- Redis Cluster (고가용성)
- TTL 기반 캐시 만료
- 예상 메모리: 10-20 GB

#### 2.2.4 메시지 큐 (RabbitMQ)

**용도**:
- 워크스페이스 생성/삭제 작업
- Git 클론 작업 (비동기)
- LLM 요청 큐잉
- 알림 전송

**구성**:
- RabbitMQ Cluster
- 여러 큐로 작업 분리

#### 2.2.5 워크스페이스 컨테이너 (Kubernetes)

**구성**:
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: ws-{workspace_id}
  labels:
    workspace-id: {workspace_id}
    owner-id: {user_id}
    org-id: {org_id}
spec:
  containers:
  - name: workspace
    image: workspace-base:latest
    resources:
      requests:
        memory: "2Gi"
        cpu: "1"
      limits:
        memory: "4Gi"
        cpu: "2"
    volumeMounts:
    - name: workspace-storage
      mountPath: /workspace
  volumes:
  - name: workspace-storage
    persistentVolumeClaim:
      claimName: ws-{workspace_id}-pvc
```

**스케일링**:
- 워크스페이스 생성 시 자동 Pod 생성
- 비활성 워크스페이스는 자동 정지 (리소스 절약)
- 필요 시 자동 재시작

---

## 3. 핵심 서비스 설계

### 3.1 Workspace Manager Service

**책임**:
- 워크스페이스 라이프사이클 관리
- Kubernetes Pod 생성/삭제
- 리소스 모니터링
- 자동 스케일링 정책 적용

**구현**:
```python
# apps/api/src/services/workspace_manager.py

from kubernetes import client, config
from kubernetes.client.rest import ApiException
import asyncio
from typing import Optional, Dict
import logging

class KubernetesWorkspaceManager:
    """Kubernetes 기반 워크스페이스 관리자"""
    
    def __init__(self):
        config.load_incluster_config()  # 클러스터 내부에서 실행
        self.core_v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.namespace = "workspaces"
    
    async def create_workspace(
        self,
        workspace_id: str,
        user_id: str,
        org_id: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict:
        """워크스페이스 Pod 생성"""
        
        # PVC 생성
        pvc = self._create_pvc(workspace_id)
        
        # Pod 생성
        pod = self._create_pod(
            workspace_id=workspace_id,
            user_id=user_id,
            org_id=org_id,
            pvc_name=pvc.metadata.name,
        )
        
        # 초기 설정 (Git clone 등)
        if source:
            await self._setup_workspace(pod.metadata.name, source)
        
        return {
            "pod_name": pod.metadata.name,
            "status": "creating",
        }
    
    def _create_pvc(self, workspace_id: str):
        """PersistentVolumeClaim 생성"""
        pvc_manifest = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"ws-{workspace_id}-pvc",
                "namespace": self.namespace,
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {
                    "requests": {
                        "storage": "50Gi"  # 기본 50GB
                    }
                },
                "storageClassName": "fast-ssd",  # SSD 스토리지
            }
        }
        
        return self.core_v1.create_namespaced_persistent_volume_claim(
            namespace=self.namespace,
            body=pvc_manifest
        )
    
    def _create_pod(self, workspace_id: str, user_id: str, org_id: Optional[str], pvc_name: str):
        """워크스페이스 Pod 생성"""
        pod_manifest = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": f"ws-{workspace_id}",
                "namespace": self.namespace,
                "labels": {
                    "workspace-id": workspace_id,
                    "owner-id": user_id,
                    "org-id": org_id or "default",
                }
            },
            "spec": {
                "containers": [{
                    "name": "workspace",
                    "image": "workspace-base:latest",
                    "workingDir": "/workspace",
                    "resources": {
                        "requests": {
                            "memory": "2Gi",
                            "cpu": "1"
                        },
                        "limits": {
                            "memory": "4Gi",
                            "cpu": "2"
                        }
                    },
                    "volumeMounts": [{
                        "name": "workspace-storage",
                        "mountPath": "/workspace"
                    }],
                    "securityContext": {
                        "runAsNonRoot": True,
                        "runAsUser": 1000,
                        "allowPrivilegeEscalation": False,
                    }
                }],
                "volumes": [{
                    "name": "workspace-storage",
                    "persistentVolumeClaim": {
                        "claimName": pvc_name
                    }
                }],
                "restartPolicy": "Always",
            }
        }
        
        return self.core_v1.create_namespaced_pod(
            namespace=self.namespace,
            body=pod_manifest
        )
    
    async def stop_workspace(self, workspace_id: str):
        """워크스페이스 정지 (리소스 절약)"""
        pod_name = f"ws-{workspace_id}"
        try:
            self.core_v1.delete_namespaced_pod(
                name=pod_name,
                namespace=self.namespace,
                grace_period_seconds=30
            )
        except ApiException as e:
            if e.status != 404:
                raise
    
    async def get_workspace_status(self, workspace_id: str) -> Dict:
        """워크스페이스 상태 조회"""
        pod_name = f"ws-{workspace_id}"
        try:
            pod = self.core_v1.read_namespaced_pod(
                name=pod_name,
                namespace=self.namespace
            )
            return {
                "status": pod.status.phase,
                "created_at": pod.metadata.creation_timestamp.isoformat(),
            }
        except ApiException as e:
            if e.status == 404:
                return {"status": "not_found"}
            raise
```

### 3.2 리소스 모니터링 서비스

**책임**:
- 워크스페이스 리소스 사용량 수집
- 메트릭 저장
- 알림 발송 (리소스 초과 시)

**구현**:
```python
# apps/api/src/services/resource_monitor.py

from prometheus_client import Counter, Gauge, Histogram
import asyncio
from kubernetes import client

class ResourceMonitor:
    """워크스페이스 리소스 모니터링"""
    
    def __init__(self):
        self.cpu_usage = Gauge('workspace_cpu_usage', 'CPU usage per workspace', ['workspace_id'])
        self.memory_usage = Gauge('workspace_memory_usage', 'Memory usage per workspace', ['workspace_id'])
        self.disk_usage = Gauge('workspace_disk_usage', 'Disk usage per workspace', ['workspace_id'])
    
    async def collect_metrics(self):
        """주기적으로 메트릭 수집"""
        while True:
            # Kubernetes Metrics API로 리소스 사용량 조회
            # Prometheus에 메트릭 전송
            await asyncio.sleep(60)  # 1분마다 수집
```

### 3.3 자동 스케일링 정책

**정책**:
1. **워크스페이스 자동 정지**
   - 30분 비활성 시 정지
   - 리소스 절약

2. **워크스페이스 자동 재시작**
   - 사용자 접근 시 자동 재시작
   - 최대 10초 내 시작

3. **노드 자동 스케일링**
   - 워크스페이스 수에 따라 노드 추가/제거
   - Spot 인스턴스 활용 (비용 절감)

---

## 4. 데이터베이스 스키마 확장

### 4.1 멀티 테넌트 지원

```sql
-- 조직 테이블
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    max_workspaces INTEGER DEFAULT 100,
    max_users INTEGER DEFAULT 500,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 사용자 테이블
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) UNIQUE NOT NULL,
    org_id VARCHAR(100) NOT NULL,
    email VARCHAR(255),
    name VARCHAR(255),
    role VARCHAR(50) NOT NULL, -- admin, developer, viewer
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (org_id) REFERENCES organizations(org_id)
);

-- 워크스페이스 할당량
CREATE TABLE workspace_quotas (
    org_id VARCHAR(100) PRIMARY KEY,
    max_workspaces INTEGER DEFAULT 100,
    max_cpu_per_workspace INTEGER DEFAULT 2,
    max_memory_per_workspace INTEGER DEFAULT 4096, -- MB
    max_storage_per_workspace INTEGER DEFAULT 50000, -- MB
    FOREIGN KEY (org_id) REFERENCES organizations(org_id)
);
```

---

## 5. 구현 로드맵

### Phase 1: 기반 인프라 (1-2주)
- [ ] Kubernetes 클러스터 설정
- [ ] PostgreSQL Primary-Replica 구성
- [ ] Redis Cluster 구성
- [ ] RabbitMQ Cluster 구성
- [ ] 모니터링 시스템 (Prometheus + Grafana)

### Phase 2: Workspace Manager 구현 (2-3주)
- [ ] KubernetesWorkspaceManager 구현
- [ ] 워크스페이스 생성/삭제 API
- [ ] 리소스 모니터링 서비스
- [ ] 자동 정지/재시작 로직

### Phase 3: 데이터베이스 통합 (1-2주)
- [ ] 워크스페이스 메타데이터 저장
- [ ] 멀티 테넌트 지원
- [ ] 감사 로그 저장
- [ ] 리소스 사용량 저장

### Phase 4: 스케일링 및 최적화 (2-3주)
- [ ] HPA 설정
- [ ] 노드 자동 스케일링
- [ ] 캐싱 전략 구현
- [ ] 성능 최적화

### Phase 5: 프로덕션 준비 (1-2주)
- [ ] 고가용성 테스트
- [ ] 부하 테스트
- [ ] 보안 감사
- [ ] 문서화

---

## 6. 비용 추정

### 인프라 비용 (월간)

**Kubernetes 클러스터**:
- Control Plane: $0 (관리형 서비스 사용 시)
- Worker Nodes (10-20개): $2,000-4,000
- Storage (15TB): $1,500-3,000

**데이터베이스**:
- PostgreSQL (Primary + Replica): $500-1,000

**캐시/큐**:
- Redis Cluster: $200-500
- RabbitMQ: $200-500

**모니터링**:
- Prometheus + Grafana: $100-200

**총 예상 비용**: $4,500-9,200/월

---

## 7. 참고 자료

- **Kubernetes Python Client**: https://github.com/kubernetes-client/python
- **Prometheus Operator**: https://github.com/prometheus-operator/prometheus-operator
- **Kubernetes Autoscaling**: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
- **PostgreSQL High Availability**: https://www.postgresql.org/docs/current/high-availability.html
