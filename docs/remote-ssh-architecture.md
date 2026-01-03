# Remote SSH 접속 아키텍처

**작성일**: 2025-01-03  
**상태**: 구현 완료 (MVP)  
**목적**: 금융권 터미널 작업을 위한 Cursor/VS Code Remote SSH 접속 지원

---

## 1. 개요

### 1.1 배경
- 금융권에서는 터미널(SSH) 접속을 통한 작업이 일반적
- Cursor IDE의 Remote SSH 기능과 연동 필요
- 워크스페이스별 격리된 SSH 접속 환경 제공

### 1.2 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      사용자 PC                               │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Cursor    │    │  터미널     │    │  VS Code    │      │
│  │ Remote SSH  │    │  (SSH)      │    │ Remote SSH  │      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          │ SSH (Port 22xxx) │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    온프레미스 서버                           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  API 서버 (FastAPI)                  │   │
│  │  - SSH 연결 정보 관리                                 │   │
│  │  - SSH 키 설정 API                                   │   │
│  │  - 컨테이너 관리                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                  │
│                    Docker │ Network                          │
│                           │                                  │
│  ┌───────────────────────────────────────────────────────┐ │
│  │             워크스페이스 컨테이너                      │ │
│  │   ┌──────────────────────────────────────────────┐   │ │
│  │   │     Ubuntu 24.04 + SSH Server                 │   │ │
│  │   │                                               │   │ │
│  │   │  - sshd (Port 22)                            │   │ │
│  │   │  - Python 3.x + venv                         │   │ │
│  │   │  - Node.js 20.x                              │   │ │
│  │   │  - Java 21 (OpenJDK)                         │   │ │
│  │   │  - Go 1.22                                   │   │ │
│  │   │  - Git, vim, htop, etc.                      │   │ │
│  │   │                                               │   │ │
│  │   │  /workspace ← 사용자 프로젝트                  │   │ │
│  │   └──────────────────────────────────────────────┘   │ │
│  │          ↑                                            │ │
│  │     Port Mapping: 22xxx:22                           │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 워크스페이스 이미지

### 2.1 Ubuntu 24.04 기반 개발 환경

```dockerfile
# docker/workspace-images/ubuntu-dev/Dockerfile
FROM ubuntu:24.04

# 사전 설치된 개발 도구
- Python 3.x + pip + venv
- Node.js 20.x + npm + pnpm + yarn
- Java 21 (OpenJDK) + Maven + Gradle
- Go 1.22
- Git, vim, nano, htop, curl, wget
- openssh-server

# 보안 설정
- 비특권 사용자 (developer, UID 1000)
- sudo 권한 (NOPASSWD)
- SSH 키/패스워드 인증 지원
```

### 2.2 이미지 빌드

```bash
# 이미지 빌드
cd docker/workspace-images/ubuntu-dev
docker build -t cursor-workspace-ubuntu:24.04 .

# 테스트 실행
docker run -d --name test-ws \
  -p 22001:22 \
  -e SSH_PASSWORD=testpass \
  cursor-workspace-ubuntu:24.04
```

---

## 3. SSH API

### 3.1 연결 정보 조회

```
GET /api/workspaces/{ws_id}/ssh/info
```

**응답**:
```json
{
  "workspaceId": "ws_project1",
  "connection": {
    "host": "server.company.com",
    "port": 22001,
    "username": "developer",
    "authType": "key"
  },
  "status": "available",
  "sshCommand": "ssh -p 22001 developer@server.company.com",
  "vscodeRemoteUri": "vscode://vscode-remote/ssh-remote+developer@server.company.com:22001/workspace"
}
```

### 3.2 SSH 공개키 설정

```
POST /api/workspaces/{ws_id}/ssh/key
```

**요청**:
```json
{
  "publicKey": "ssh-ed25519 AAAA... user@example.com"
}
```

### 3.3 SSH 키 쌍 생성

```
POST /api/workspaces/{ws_id}/ssh/generate
```

**요청**:
```json
{
  "key_type": "ed25519"
}
```

**응답**:
```json
{
  "success": true,
  "publicKey": "ssh-ed25519 AAAA...",
  "privateKey": "-----BEGIN OPENSSH PRIVATE KEY-----...",
  "fingerprint": "SHA256:..."
}
```

### 3.4 Cursor SSH 접속 설정

```
GET /api/workspaces/{ws_id}/ssh/cursor-command
```

**응답**:
```json
{
  "instructions": {
    "step1": "Cursor에서 Ctrl+Shift+P 실행",
    "step2": "'Remote-SSH: Connect to Host...' 선택",
    "step3": "'ssh -p 22001 developer@server' 입력"
  },
  "sshConfig": {
    "content": "Host cursor-ws_project1\n  HostName server\n  Port 22001\n  User developer"
  }
}
```

---

## 4. 사용 방법

### 4.1 터미널 SSH 접속

```bash
# 직접 접속
ssh -p 22001 developer@server.company.com

# SSH 설정 사용
# ~/.ssh/config 추가 후
ssh cursor-ws_project1
```

### 4.2 Cursor Remote SSH 접속

1. **Ctrl+Shift+P** (macOS: Cmd+Shift+P)
2. **"Remote-SSH: Connect to Host..."** 선택
3. **SSH 명령어 입력**: `ssh -p 22001 developer@server.company.com`
4. 연결 완료 후 `/workspace` 폴더에서 작업

### 4.3 SSH 설정 파일 활용

`~/.ssh/config`에 추가:
```
Host cursor-ws_project1
    HostName server.company.com
    Port 22001
    User developer
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
```

---

## 5. 보안 고려사항

### 5.1 인증 방식
- **SSH 키 인증** (권장): Ed25519 또는 RSA-4096
- **비밀번호 인증**: 복잡도 요구 (8자 이상, 대소문자+숫자)

### 5.2 네트워크 격리
- 각 워크스페이스는 독립된 포트 사용 (22000-22999)
- 컨테이너 간 네트워크 격리
- 필요시 방화벽 규칙 적용

### 5.3 감사 로깅
- SSH 접속 로그 기록
- 명령 실행 이력 (선택적)
- 파일 변경 이력

---

## 6. 포트 할당 전략

### 6.1 동적 포트 할당
```python
# 워크스페이스 ID를 해시하여 일관된 포트 생성
def get_ssh_port(workspace_id: str) -> int:
    hash_val = int(hashlib.md5(workspace_id.encode()).hexdigest()[:8], 16)
    return SSH_PORT_BASE + (hash_val % 1000)  # 22000-22999
```

### 6.2 환경변수 설정
```bash
SSH_PORT_BASE=22000  # 시작 포트
SSH_HOST=server.company.com  # 외부 접속 호스트
```

---

## 7. 향후 계획

1. **SSH 게이트웨이**: 단일 진입점으로 라우팅
2. **2FA 지원**: TOTP 기반 추가 인증
3. **세션 관리**: 유휴 세션 자동 종료
4. **감사 로그**: 상세한 접속/명령 이력
5. **Kubernetes 지원**: Pod 기반 SSH 접속

---

## 8. 참고 자료

- [VS Code Remote - SSH](https://code.visualstudio.com/docs/remote/ssh)
- [OpenSSH](https://www.openssh.com/)
- [Docker SSH Best Practices](https://docs.docker.com/engine/examples/running_ssh_service/)
