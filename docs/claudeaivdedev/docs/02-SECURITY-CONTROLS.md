# 02. 보안 통제 명세서

> **문서 버전**: 2.0  
> **작성일**: 2026-01-03  
> **상태**: Draft

## 1. 개요

### 1.1 목적

금융권 VDE 환경에서 Web IDE + AI 코딩 환경의 보안 통제 요건을 정의합니다.

### 1.2 규제 매핑

| 통제 영역 | 전자금융감독규정 | 개인정보보호법 | 금융보안원 가이드 |
|----------|---------------|--------------|-----------------|
| 접근통제 | 제13조 | - | 5.1 |
| 인증 | 제14조 | - | 5.2 |
| 감사추적 | 제15조 | 제29조 | 5.4 |
| 데이터 보호 | - | 제24조 | 6.1 |

## 2. 접근통제

### 2.1 인증 (Authentication)

#### 2.1.1 SSO + MFA 필수

| 요건 | 구현 방안 | 검증 방법 |
|------|----------|----------|
| SSO | Keycloak OIDC 연동 | 로그인 플로우 테스트 |
| MFA | TOTP 또는 Push 알림 | 2차 인증 강제 확인 |
| 세션 타임아웃 | 30분 미활동 시 자동 로그아웃 | 세션 만료 테스트 |
| 동시 세션 제한 | 사용자당 1세션 | 중복 로그인 차단 확인 |

#### 2.1.2 Keycloak 설정 체크리스트

```
☐ OIDC 클라이언트 등록 (code-server용)
☐ MFA 정책 활성화 (Conditional OTP)
☐ 브루트포스 방어 활성화 (5회 실패 시 잠금)
☐ 세션 정책 설정 (30분 타임아웃)
☐ 감사 로그 활성화
☐ TLS 인증서 적용 (사내 PKI)
```

### 2.2 인가 (Authorization)

#### 2.2.1 역할 기반 접근제어 (RBAC)

| 역할 | 권한 | 대상 |
|------|------|------|
| `developer` | IDE 접근, 자신의 워크스페이스 | 일반 개발자 |
| `senior-developer` | developer + 확장 설치 요청 | 선임 개발자 |
| `admin` | 모든 권한, 시스템 설정 | 운영팀 |
| `auditor` | 읽기 전용, 로그 조회 | 감사팀 |

#### 2.2.2 워크스페이스 격리

```yaml
# 네임스페이스 기반 격리
apiVersion: v1
kind: Namespace
metadata:
  name: ide-user-{{user_id}}
  labels:
    user: "{{user_id}}"
    team: "{{team}}"
---
# 네트워크 정책 - 다른 사용자 네임스페이스 접근 차단
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-cross-namespace
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ide-user-{{user_id}}
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              shared: "true"  # AI, Git 등 공유 서비스만 허용
```

### 2.3 네트워크 접근통제

#### 2.3.1 IP 허용 목록

| 소스 | 설명 |
|------|------|
| VDE 게이트웨이 IP 대역 | VDE 내부에서만 접근 허용 |
| 운영자 VPN IP | 관리 목적 접근 |

#### 2.3.2 방화벽 규칙 (요약)

| 규칙 | 소스 | 목적지 | 포트 | 허용/차단 |
|------|------|--------|------|----------|
| VDE 접속 | VDE 대역 | Nginx | 443 | 허용 |
| 인터넷 | IDE 존 | Any | Any | **차단** |
| AI 접근 | IDE 존 | AI 존 | 8081, 4000 | 허용 |
| Git 접근 | IDE 존 | GitLab | 443 | 허용 |

## 3. 데이터 보호

### 3.1 데이터 분류

| 분류 | 예시 | 보호 수준 |
|------|------|----------|
| **기밀** | 소스코드, 비즈니스 로직 | 암호화, 접근로그 |
| **내부** | 개발 문서, 설정 파일 | 접근제어 |
| **공개** | 오픈소스 라이브러리 | 무결성 검증 |

### 3.2 데이터 흐름 통제

#### 3.2.1 반출 차단

| 경로 | 통제 방법 |
|------|----------|
| 브라우저 다운로드 | VDE 정책으로 차단 |
| 클립보드 | VDE 정책으로 차단 |
| Git Push (외부) | 네트워크 차단 |
| LLM 프롬프트 | 사내 Gateway만 허용 |

#### 3.2.2 반입 통제

| 대상 | 승인 프로세스 |
|------|-------------|
| VS Code 확장 (VSIX) | 보안팀 검토 → 화이트리스트 등록 |
| 패키지 (npm, pip) | 내부 미러를 통해서만 설치 |
| 모델 파일 | 해시 검증 + 보안 스캔 후 반입 |
| 컨테이너 이미지 | 내부 레지스트리만 사용 |

### 3.3 LLM 프롬프트/응답 정책

#### 3.3.1 기본 정책 (권장)

```yaml
llm_data_policy:
  prompt_logging: false        # 프롬프트 본문 저장 안 함
  response_logging: false      # 응답 본문 저장 안 함
  metadata_logging: true       # 메타데이터(사용자, 시간, 토큰수)만 저장
  retention_days: 90           # 90일 후 자동 삭제
```

#### 3.3.2 감사 대응 정책 (선택)

특정 상황에서 전문 로깅이 필요한 경우:

```yaml
audit_mode:
  enabled: false               # 기본 비활성화
  trigger: "security_incident" # 보안 사건 발생 시만 활성화
  scope: "specific_user"       # 특정 사용자만 대상
  encryption: true             # 로그 암호화 필수
  access_control: "auditor"    # 감사팀만 접근
```

### 3.4 민감정보 탐지 (DLP)

LLM Gateway에서 DLP 룰 적용:

```yaml
dlp_rules:
  - name: "주민등록번호"
    pattern: '\d{6}-[1-4]\d{6}'
    action: mask  # 마스킹 처리
    
  - name: "신용카드번호"
    pattern: '\d{4}-\d{4}-\d{4}-\d{4}'
    action: block  # 요청 차단
    
  - name: "API 키"
    pattern: '(api[_-]?key|secret)["\s:=]+["\']?[\w-]{20,}'
    action: alert  # 알림만
```

## 4. 공급망 보안

### 4.1 확장(Extension) 관리

#### 4.1.1 화이트리스트 운영

```
승인된 확장 목록 (예시):
─────────────────────────────────
☑ ms-python.python (v2024.x)
☑ continue.continue (v0.9.x)
☑ TabbyML.vscode-tabby (v1.x)
☑ dbaeumer.vscode-eslint (v3.x)
☑ esbenp.prettier-vscode (v10.x)
─────────────────────────────────
```

#### 4.1.2 확장 반입 절차

```
1. 개발자 요청 (JIRA 티켓)
       ↓
2. 보안팀 검토
   - 소스코드 검토 (가능한 경우)
   - 권한 분석 (파일/네트워크 접근)
   - 알려진 취약점 확인
       ↓
3. 승인/반려
       ↓
4. 화이트리스트 등록 + 내부 저장소 배포
       ↓
5. 설치 이력 로깅
```

### 4.2 패키지 미러 운영

| 언어/도구 | 내부 미러 | 동기화 주기 |
|----------|----------|-----------|
| Python | Nexus (PyPI proxy) | 일 1회 |
| Node.js | Nexus (npm proxy) | 일 1회 |
| Java | Nexus (Maven) | 일 1회 |
| OS | apt mirror | 주 1회 |

#### 4.2.1 pip 설정 강제

```ini
# /etc/pip.conf (컨테이너 이미지에 포함)
[global]
index-url = https://nexus.internal/repository/pypi-proxy/simple/
trusted-host = nexus.internal
```

### 4.3 모델 파일 반입

> **⚠️ 원문에서 누락된 중요 사항**: 폐쇄망에서 AI 모델 반입은 수 GB~수십 GB 단위이므로 별도 절차 필요

#### 4.3.1 모델 반입 절차

```
1. 모델 선정 및 요청
   - 모델명, 버전, 용도 명시
   - 라이선스 검토 (상업적 사용 가능 여부)
       ↓
2. 외부망에서 다운로드
   - 공식 소스에서 다운로드 (HuggingFace, GitHub)
   - SHA256 해시 기록
       ↓
3. 보안 스캔
   - 파일 무결성 검증
   - 악성코드 스캔
       ↓
4. 반입 매체 이동
   - 승인된 매체(USB, 전용 전송 시스템)로 이동
   - 반입 대장 작성
       ↓
5. 내부 저장소 등록
   - 버전 관리 (model-registry)
   - 메타데이터 기록 (해시, 날짜, 담당자)
```

### 4.4 SBOM (Software Bill of Materials)

컨테이너 이미지별 SBOM 생성 및 관리:

```bash
# Syft를 사용한 SBOM 생성
syft code-server-image:latest -o spdx-json > sbom-code-server.json

# Grype를 사용한 취약점 스캔
grype sbom:sbom-code-server.json
```

## 5. 감사 로깅

### 5.1 로그 수집 대상

| 계층 | 로그 유형 | 보존 기간 | 중요도 |
|------|----------|----------|-------|
| **인증** | SSO 로그인/로그아웃 | 1년 | 필수 |
| **접근** | Nginx 접근 로그 | 90일 | 필수 |
| **시스템** | sudo, auditd | 90일 | 필수 |
| **애플리케이션** | IDE 세션 이벤트 | 90일 | 권장 |
| **AI** | LLM 요청 메타데이터 | 90일 | 권장 |

### 5.2 필수 로그 필드

#### 5.2.1 인증 로그

```json
{
  "timestamp": "2026-01-03T10:30:00Z",
  "event_type": "login",
  "user_id": "user123",
  "source_ip": "10.0.2.50",
  "result": "success",
  "mfa_method": "totp",
  "session_id": "sess_abc123"
}
```

#### 5.2.2 IDE 세션 로그

```json
{
  "timestamp": "2026-01-03T10:31:00Z",
  "event_type": "ide_session_start",
  "user_id": "user123",
  "workspace_id": "ws_xyz789",
  "container_id": "ctr_def456",
  "allocated_resources": {
    "cpu": "2",
    "memory": "4Gi"
  }
}
```

#### 5.2.3 AI 요청 메타데이터 (본문 제외)

```json
{
  "timestamp": "2026-01-03T10:35:00Z",
  "event_type": "llm_request",
  "user_id": "user123",
  "model": "deepseek-coder-33b",
  "request_type": "chat",
  "input_tokens": 150,
  "output_tokens": 200,
  "latency_ms": 1200,
  "dlp_triggered": false
}
```

### 5.3 터미널 명령 감사 (⚠️ 민감)

> **주의**: 터미널 전문 로깅은 개인정보/영업비밀 이슈가 있으므로 단계적 적용 권장

| 단계 | 범위 | 적용 시점 |
|------|------|----------|
| 1단계 | 프로세스 실행 이벤트만 (명령줄 인자 제외) | 초기 |
| 2단계 | 특정 명령어만 (sudo, git push 등) | 파일럿 |
| 3단계 | 전문 로깅 (암호화 + 접근통제) | 운영 (선택) |

### 5.4 SIEM 연동

```yaml
# Filebeat 설정 예시
filebeat.inputs:
  - type: container
    paths:
      - '/var/log/containers/*code-server*.log'
    processors:
      - add_kubernetes_metadata:
          host: ${NODE_NAME}

output.elasticsearch:
  hosts: ["https://elasticsearch.internal:9200"]
  ssl.certificate_authorities: ["/etc/pki/ca.crt"]
  index: "ide-logs-%{+yyyy.MM.dd}"
```

## 6. 취약점 관리

### 6.1 정기 스캔 일정

| 대상 | 도구 | 주기 | 담당 |
|------|------|------|------|
| 컨테이너 이미지 | Trivy | 빌드 시 + 주 1회 | DevOps |
| 호스트 OS | OpenSCAP | 월 1회 | 인프라팀 |
| 웹 애플리케이션 | OWASP ZAP | 분기 1회 | 보안팀 |
| 의존성 패키지 | Dependabot/Snyk | 실시간 | DevOps |

### 6.2 패치 정책

| 취약점 등급 | 패치 기한 | 승인 절차 |
|-----------|----------|----------|
| Critical (CVSS 9.0+) | 24시간 | 긴급 승인 |
| High (CVSS 7.0-8.9) | 7일 | 일반 승인 |
| Medium (CVSS 4.0-6.9) | 30일 | 정기 배포 |
| Low (CVSS 0.1-3.9) | 90일 | 정기 배포 |

## 7. 보안 체크리스트 (심사 대응용)

### 7.1 접근통제

```
☐ SSO 연동 완료
☐ MFA 강제 적용
☐ 세션 타임아웃 설정 (30분 이하)
☐ 동시 세션 제한 (1세션)
☐ IP 허용 목록 적용
☐ 사용자별 워크스페이스 격리
```

### 7.2 데이터 보호

```
☐ 인터넷 접근 완전 차단
☐ 파일 반출입 통제
☐ LLM 프롬프트 사내 Gateway만 허용
☐ DLP 룰 적용
☐ 민감정보 마스킹
```

### 7.3 공급망

```
☐ 확장 화이트리스트 운영
☐ 패키지 미러 구성
☐ 모델 반입 절차 수립
☐ SBOM 생성
☐ 컨테이너 이미지 스캔
```

### 7.4 감사

```
☐ 인증 로그 수집
☐ 접근 로그 수집
☐ 시스템 감사 로그 (auditd)
☐ IDE 세션 로그
☐ AI 요청 메타데이터 로그
☐ SIEM 연동
☐ 로그 보존 정책 (1년)
```

## 8. 다음 단계

- [운영 가이드](03-OPERATIONS-GUIDE.md)에서 일상 운영 절차 확인
- [scaffold/configs/](../scaffold/configs/)에서 보안 설정 파일 확인
