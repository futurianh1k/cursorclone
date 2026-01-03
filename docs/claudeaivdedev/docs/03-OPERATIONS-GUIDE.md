# 03. 운영 가이드

> **문서 버전**: 2.0  
> **작성일**: 2026-01-03  
> **상태**: Draft

## 1. 개요

### 1.1 목적

Web IDE + AI 코딩 환경의 일상 운영, 장애 대응, 업데이트 절차를 정의합니다.

### 1.2 운영 조직

| 역할 | 담당 업무 | 연락처 |
|------|----------|-------|
| 플랫폼 관리자 | 인프라 운영, 배포, 장애 대응 | platform-admin@company.com |
| 보안 담당자 | 접근통제, 감사, 취약점 관리 | security@company.com |
| 사용자 지원 | 문의 응대, 계정 관리 | helpdesk@company.com |

## 2. 일상 운영

### 2.1 일일 점검 체크리스트

```
□ 08:00 - 서비스 상태 확인
  ├─ □ Nginx 프록시 응답 확인
  ├─ □ Keycloak 인증 정상 확인
  ├─ □ code-server 헬스체크
  ├─ □ Tabby 서버 응답 시간 확인 (< 300ms)
  └─ □ LLM Gateway 상태 확인

□ 09:00 - 리소스 모니터링
  ├─ □ GPU 사용률 (< 80% 권장)
  ├─ □ 메모리 사용률 (< 85%)
  ├─ □ 디스크 사용률 (< 80%)
  └─ □ 활성 세션 수

□ 17:00 - 보안 점검
  ├─ □ 인증 실패 로그 검토
  ├─ □ 비정상 접근 패턴 확인
  └─ □ DLP 알림 확인
```

### 2.2 모니터링 대시보드

#### 2.2.1 핵심 메트릭

| 메트릭 | 정상 범위 | 경고 임계값 | 위험 임계값 |
|--------|----------|-----------|-----------|
| IDE 응답 시간 | < 500ms | > 1s | > 3s |
| 자동완성 응답 (P95) | < 250ms | > 400ms | > 1s |
| Chat 응답 (P95) | < 3s | > 5s | > 10s |
| GPU 사용률 | 30-70% | > 80% | > 95% |
| 활성 세션 | - | > 80% 용량 | > 95% 용량 |

#### 2.2.2 Grafana 대시보드 구성

```
┌─────────────────────────────────────────────────────────────┐
│  Web IDE Platform Dashboard                                  │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│ │ Active Users │ │ Avg Latency  │ │ Error Rate   │          │
│ │     45       │ │    180ms     │ │    0.1%      │          │
│ └──────────────┘ └──────────────┘ └──────────────┘          │
├─────────────────────────────────────────────────────────────┤
│ [Response Time Graph]                                        │
│ ──────────────────────────────                              │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ [GPU Utilization]        [Memory Usage]                     │
│ ████████░░ 75%           ███████░░░ 68%                     │
├─────────────────────────────────────────────────────────────┤
│ [AI Request Metrics]                                         │
│ Autocomplete: 1,234 req/min | Chat: 89 req/min              │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 알림 설정

```yaml
# alertmanager.yml
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'platform-team'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'
    - match:
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'platform-team'
    email_configs:
      - to: 'platform-admin@company.com'
        
  - name: 'slack'
    slack_configs:
      - channel: '#ide-alerts'
        
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '<service_key>'
```

## 3. 사용자 관리

### 3.1 계정 생성 절차

```
1. 사용자 요청 (JIRA 티켓)
   - 부서, 역할, 필요 권한 명시
       ↓
2. 관리자 승인
   - 부서장 승인
   - 보안팀 검토 (필요시)
       ↓
3. Keycloak 계정 생성
   - 그룹/역할 할당
   - MFA 등록 안내
       ↓
4. 워크스페이스 프로비저닝
   - 네임스페이스 생성
   - PVC 할당
   - 기본 설정 적용
       ↓
5. 사용자 안내
   - 접속 URL
   - 초기 설정 가이드
```

### 3.2 계정 비활성화

```bash
#!/bin/bash
# disable_user.sh

USER_ID=$1

# 1. Keycloak 계정 비활성화
kcadm.sh update users/${USER_ID} -s enabled=false

# 2. 활성 세션 강제 종료
kubectl delete pod -l user=${USER_ID} -n ide-${USER_ID}

# 3. 워크스페이스 보존 (감사 목적)
kubectl annotate namespace ide-${USER_ID} \
  "disabled-at=$(date -Iseconds)" \
  "disabled-by=${ADMIN_USER}"

echo "User ${USER_ID} disabled. Workspace preserved for audit."
```

### 3.3 리소스 쿼터 조정

```yaml
# 기본 쿼터 (일반 개발자)
apiVersion: v1
kind: ResourceQuota
metadata:
  name: default-quota
spec:
  hard:
    requests.cpu: "2"
    requests.memory: "4Gi"
    limits.cpu: "4"
    limits.memory: "8Gi"
    persistentvolumeclaims: "2"
    requests.storage: "20Gi"

---
# 고급 쿼터 (시니어 개발자 / 특수 프로젝트)
apiVersion: v1
kind: ResourceQuota
metadata:
  name: elevated-quota
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    limits.cpu: "8"
    limits.memory: "16Gi"
    persistentvolumeclaims: "4"
    requests.storage: "50Gi"
```

## 4. 확장(Extension) 관리

### 4.1 확장 승인 프로세스

```
┌─────────────────────────────────────────────────────────────┐
│                    확장 승인 워크플로우                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [개발자 요청] ──► [보안팀 검토] ──► [승인] ──► [배포]         │
│       │              │              │          │            │
│       ▼              ▼              ▼          ▼            │
│   JIRA 티켓      보안 분석       화이트리스트   내부 저장소    │
│   - 확장명       - 권한 검토        등록        VSIX 배포     │
│   - 용도        - CVE 확인                                  │
│   - 버전        - 소스 검토                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 화이트리스트 관리

```yaml
# extensions-whitelist.yaml
extensions:
  # 언어 지원
  - id: ms-python.python
    version: "2024.22.x"
    approved_date: "2026-01-01"
    approved_by: "security-team"
    
  # AI 코딩
  - id: continue.continue
    version: "0.9.x"
    approved_date: "2026-01-01"
    approved_by: "security-team"
    notes: "LLM 엔드포인트는 내부 Gateway만 허용"
    
  - id: TabbyML.vscode-tabby
    version: "1.x"
    approved_date: "2026-01-01"
    approved_by: "security-team"
    
  # 코드 품질
  - id: dbaeumer.vscode-eslint
    version: "3.x"
    approved_date: "2026-01-01"
    approved_by: "security-team"

blocked_extensions:
  - id: "*remote*"
    reason: "원격 접속 기능 차단"
  - id: "*copilot*"
    reason: "외부 AI 서비스 차단"
```

### 4.3 확장 배포 자동화

```bash
#!/bin/bash
# deploy_extension.sh

VSIX_FILE=$1
EXTENSION_ID=$2

# 1. 해시 검증
EXPECTED_HASH=$(grep ${EXTENSION_ID} extensions-hashes.txt | cut -d' ' -f1)
ACTUAL_HASH=$(sha256sum ${VSIX_FILE} | cut -d' ' -f1)

if [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
    echo "ERROR: Hash mismatch for ${EXTENSION_ID}"
    exit 1
fi

# 2. 내부 저장소에 업로드
curl -X PUT \
    -H "Content-Type: application/octet-stream" \
    --data-binary @${VSIX_FILE} \
    "https://nexus.internal/repository/vsix/${EXTENSION_ID}.vsix"

# 3. 설치 로그
echo "$(date -Iseconds) | ${ADMIN_USER} | DEPLOY | ${EXTENSION_ID}" >> /var/log/extension-audit.log

echo "Extension ${EXTENSION_ID} deployed successfully"
```

## 5. 모델 업데이트

### 5.1 모델 업데이트 절차

```
Phase 1: 준비 (D-7)
──────────────────
□ 새 모델 버전 다운로드 (외부망)
□ 해시 및 라이선스 확인
□ 보안 스캔
□ 반입 승인

Phase 2: 테스트 (D-3)
──────────────────
□ 스테이징 환경 배포
□ 성능 벤치마크 (응답시간, 품질)
□ 회귀 테스트
□ 리소스 사용량 확인

Phase 3: 배포 (D-Day)
──────────────────
□ 공지 (사용자 알림)
□ 롤링 업데이트 실행
□ 헬스체크 확인
□ 모니터링 강화

Phase 4: 검증 (D+1)
──────────────────
□ 사용자 피드백 수집
□ 에러율 확인
□ 롤백 여부 결정
```

### 5.2 롤링 업데이트 스크립트

```bash
#!/bin/bash
# update_model.sh

NEW_MODEL_PATH=$1
SERVICE=$2  # tabby or vllm

# 1. 현재 버전 백업
CURRENT_VERSION=$(kubectl get deployment ${SERVICE} -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="MODEL_PATH")].value}')
echo "Current model: ${CURRENT_VERSION}"

# 2. Canary 배포 (10% 트래픽)
kubectl patch deployment ${SERVICE} \
    -p '{"spec":{"strategy":{"rollingUpdate":{"maxSurge":"10%","maxUnavailable":"0%"}}}}'

# 3. 새 모델로 업데이트
kubectl set env deployment/${SERVICE} MODEL_PATH=${NEW_MODEL_PATH}

# 4. 상태 확인
kubectl rollout status deployment/${SERVICE} --timeout=10m

if [ $? -ne 0 ]; then
    echo "ERROR: Rollout failed. Rolling back..."
    kubectl rollout undo deployment/${SERVICE}
    exit 1
fi

echo "Model update completed successfully"
```

## 6. 장애 대응

### 6.1 장애 등급 정의

| 등급 | 설명 | 대응 시간 | 에스컬레이션 |
|------|------|----------|-------------|
| P1 | 전체 서비스 중단 | 15분 이내 | 즉시 |
| P2 | 핵심 기능 장애 (AI, 인증) | 30분 이내 | 1시간 |
| P3 | 일부 사용자 영향 | 2시간 이내 | 4시간 |
| P4 | 경미한 이슈 | 24시간 이내 | 필요시 |

### 6.2 장애 대응 플로우

```
┌──────────┐
│ 장애 감지 │
└────┬─────┘
     │
     ▼
┌──────────┐     Yes    ┌──────────┐
│ 자동 복구 │────────────►│   종료    │
│ 가능?    │            └──────────┘
└────┬─────┘
     │ No
     ▼
┌──────────┐
│ 영향 범위 │
│ 분석     │
└────┬─────┘
     │
     ├─── P1 ──► 전체 공지 + 비상 대응팀 소집
     │
     ├─── P2 ──► 담당자 알림 + 영향 사용자 공지
     │
     └─── P3/P4 ─► 티켓 생성 + 일반 대응
```

### 6.3 주요 장애 시나리오 및 대응

#### 6.3.1 IDE 접속 불가

```bash
# 진단 체크리스트
□ Nginx 상태 확인
  kubectl get pods -l app=nginx -n ingress

□ Keycloak 상태 확인
  kubectl get pods -l app=keycloak -n auth

□ 네트워크 정책 확인
  kubectl get networkpolicy -A

□ TLS 인증서 만료 확인
  openssl s_client -connect ide.company.com:443 2>/dev/null | openssl x509 -noout -dates

# 긴급 대응
- Nginx 재시작: kubectl rollout restart deployment/nginx -n ingress
- Keycloak 재시작: kubectl rollout restart deployment/keycloak -n auth
```

#### 6.3.2 AI 자동완성 느림/불가

```bash
# 진단
□ Tabby 서버 상태
  curl -w "%{time_total}\n" http://tabby-server:8080/health

□ GPU 상태
  nvidia-smi

□ 모델 로딩 상태
  kubectl logs deployment/tabby | grep -i "model loaded"

# 대응
- 캐시 클리어: kubectl exec deployment/tabby -- /app/clear-cache.sh
- 서버 재시작: kubectl rollout restart deployment/tabby
- GPU 리소스 부족 시: 스케일 아웃
```

#### 6.3.3 사용자 워크스페이스 접근 불가

```bash
# 진단
□ 사용자 Pod 상태
  kubectl get pods -n ide-${USER_ID}

□ PVC 상태
  kubectl get pvc -n ide-${USER_ID}

□ 이벤트 확인
  kubectl get events -n ide-${USER_ID} --sort-by='.lastTimestamp'

# 대응
- Pod 재생성: kubectl delete pod -l user=${USER_ID} -n ide-${USER_ID}
- PVC 복구 (백업에서): velero restore create --from-backup ${BACKUP_NAME}
```

### 6.4 롤백 절차

```bash
#!/bin/bash
# rollback.sh

COMPONENT=$1  # nginx, code-server, tabby, vllm, litellm
REVISION=$2   # 롤백할 리비전 (optional)

if [ -z "$REVISION" ]; then
    # 이전 버전으로 롤백
    kubectl rollout undo deployment/${COMPONENT}
else
    # 특정 리비전으로 롤백
    kubectl rollout undo deployment/${COMPONENT} --to-revision=${REVISION}
fi

# 롤백 확인
kubectl rollout status deployment/${COMPONENT}

# 감사 로그
echo "$(date -Iseconds) | ${ADMIN_USER} | ROLLBACK | ${COMPONENT} | ${REVISION}" >> /var/log/deployment-audit.log
```

## 7. 백업 및 복구

### 7.1 백업 대상 및 주기

| 대상 | 방법 | 주기 | 보존 기간 |
|------|------|------|----------|
| 사용자 워크스페이스 | Velero (PVC 스냅샷) | 일 1회 | 30일 |
| Keycloak DB | pg_dump | 6시간 | 30일 |
| GitLab | GitLab 내장 백업 | 일 1회 | 90일 |
| 설정 파일 (ConfigMap/Secret) | etcd 스냅샷 | 일 1회 | 30일 |
| 모델 파일 | Object Storage 복제 | 실시간 | 영구 |

### 7.2 백업 자동화

```yaml
# velero-schedule.yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-workspace-backup
spec:
  schedule: "0 2 * * *"  # 매일 02:00
  template:
    includedNamespaces:
      - "ide-*"
    includedResources:
      - persistentvolumeclaims
      - configmaps
      - secrets
    storageLocation: default
    ttl: 720h  # 30일
```

### 7.3 복구 테스트

```
□ 월 1회 복구 테스트 실시
□ 테스트 항목:
  - 개별 사용자 워크스페이스 복구
  - Keycloak DB 복구
  - 전체 네임스페이스 복구
□ 복구 소요 시간 측정 및 기록
□ 결과 보고서 작성
```

## 8. 성능 튜닝

### 8.1 code-server 최적화

```json
// settings.json (기본 설정)
{
  "files.autoSave": "afterDelay",
  "files.autoSaveDelay": 60000,
  "files.watcherExclude": {
    "**/node_modules/**": true,
    "**/.git/**": true,
    "**/dist/**": true
  },
  "search.exclude": {
    "**/node_modules": true,
    "**/dist": true
  },
  "extensions.autoUpdate": false,
  "telemetry.telemetryLevel": "off"
}
```

### 8.2 Tabby 성능 튜닝

```yaml
# tabby 배포 설정
env:
  - name: TABBY_SCHEDULER_MAX_BATCH_SIZE
    value: "4"
  - name: TABBY_SCHEDULER_MAX_WAITING_TOKENS
    value: "1024"
  - name: TABBY_MODEL_CACHE_DIR
    value: "/models"
resources:
  limits:
    nvidia.com/gpu: 1
    memory: "24Gi"
  requests:
    nvidia.com/gpu: 1
    memory: "16Gi"
```

### 8.3 성능 벤치마크 기준

> **⚠️ PoC 성공 기준** (원문에서 누락된 정량적 기준)

| 메트릭 | 최소 기준 | 목표 | 측정 방법 |
|--------|----------|------|----------|
| 자동완성 응답 (P95) | < 400ms | < 200ms | Tabby 메트릭 |
| 자동완성 수용률 | > 15% | > 25% | 사용자 피드백 |
| Chat 응답 (P95) | < 5s | < 3s | LLM Gateway 메트릭 |
| IDE 로딩 시간 | < 10s | < 5s | Lighthouse |
| 일일 가동률 | > 99% | > 99.5% | 모니터링 |

## 9. 정기 작업 일정

### 9.1 주간 작업

```
□ 월요일: 지난 주 장애/이슈 리뷰
□ 화요일: 보안 패치 검토 및 적용 계획
□ 수요일: 확장 승인 요청 처리
□ 목요일: 용량 계획 검토
□ 금요일: 주간 리포트 작성
```

### 9.2 월간 작업

```
□ 첫째 주: 취약점 스캔 및 패치
□ 둘째 주: 백업 복구 테스트
□ 셋째 주: 용량 계획 및 스케일링 검토
□ 넷째 주: 문서 업데이트 및 교육
```

## 10. 연락처 및 에스컬레이션

| 상황 | 1차 연락 | 2차 연락 (30분 무응답) |
|------|---------|---------------------|
| P1 장애 | On-call 당직자 | 팀장 + 임원 |
| P2 장애 | 플랫폼팀 | On-call 당직자 |
| 보안 이슈 | 보안팀 | CISO |
| 사용자 문의 | 헬프데스크 | 플랫폼팀 |
