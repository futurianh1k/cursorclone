# 파일 전송 가이드

**작성일**: 2025-01-03  
**목적**: 금융권 폐쇄망 환경에서 파일/패키지 업로드 방법 안내

---

## 1. 개요

금융권 폐쇄망 환경에서는 GitHub 접속이나 외부 패키지 저장소(npm, PyPI, Maven 등) 접근이 제한됩니다.
이 가이드는 다양한 방법으로 파일과 패키지를 워크스페이스에 전송하는 방법을 설명합니다.

### 지원하는 전송 방법

| 방법 | 용도 | 속도 | 권장 상황 |
|------|------|------|----------|
| **웹 UI 업로드** | 소규모 파일 | 보통 | 빠른 업로드, 비개발자 |
| **ZIP 업로드** | 프로젝트/패키지 | 빠름 | node_modules, vendor 등 대용량 |
| **SCP/SFTP** | 대용량 파일 | 빠름 | 개발자, 자동화 스크립트 |
| **Cursor Remote** | 직접 편집 | 실시간 | 개발 작업 |

---

## 2. 웹 UI 파일 업로드

### 2.1 단일/다중 파일 업로드

1. 워크스페이스에서 **"📤 파일 업로드"** 패널 열기
2. 파일을 드래그 앤 드롭 또는 **"파일 선택"** 버튼 클릭
3. 대상 디렉토리 지정 (선택사항)
4. 업로드 완료 확인

**제한사항**:
- 단일 파일: 최대 100MB
- 허용 확장자: .py, .js, .ts, .java, .go, .json, .yaml, .md 등

### 2.2 ZIP 아카이브 업로드

대용량 프로젝트나 패키지는 ZIP으로 압축하여 업로드:

```bash
# 로컬 PC에서 ZIP 생성
zip -r project.zip src/ package.json

# 패키지 폴더 압축
zip -r node_modules.zip node_modules/
zip -r vendor.zip vendor/
```

1. **"📦 ZIP 업로드"** 버튼 클릭
2. ZIP 파일 선택
3. 자동으로 워크스페이스에 압축 해제

**제한사항**:
- ZIP 파일: 최대 500MB
- 압축 해제 후 총 용량: 최대 5GB

---

## 3. SCP/SFTP 파일 전송

### 3.1 SCP (Secure Copy)

SSH 접속이 가능하면 SCP로 파일을 직접 전송할 수 있습니다.

```bash
# SSH 연결 정보 확인
# 호스트: server.company.com
# 포트: 22001
# 사용자: developer

# 단일 파일 업로드
scp -P 22001 local_file.py developer@server.company.com:/workspace/

# 디렉토리 업로드 (재귀적)
scp -P 22001 -r local_folder/ developer@server.company.com:/workspace/

# 여러 파일 업로드
scp -P 22001 *.py developer@server.company.com:/workspace/src/

# 파일 다운로드
scp -P 22001 developer@server.company.com:/workspace/result.txt ./
```

### 3.2 SFTP (SSH File Transfer Protocol)

대화형 파일 전송이 필요할 때 SFTP 사용:

```bash
# SFTP 연결
sftp -P 22001 developer@server.company.com

# SFTP 명령어
sftp> pwd                     # 현재 경로 확인
sftp> cd /workspace           # 디렉토리 이동
sftp> lcd /local/path         # 로컬 디렉토리 이동
sftp> put file.py             # 파일 업로드
sftp> put -r folder/          # 디렉토리 업로드
sftp> get remote_file.py      # 파일 다운로드
sftp> get -r folder/          # 디렉토리 다운로드
sftp> ls                      # 파일 목록
sftp> exit                    # 종료
```

### 3.3 rsync (권장 - 대용량/증분 동기화)

rsync는 변경된 파일만 전송하여 효율적입니다:

```bash
# 기본 동기화
rsync -avz -e "ssh -p 22001" local_folder/ developer@server.company.com:/workspace/

# 삭제된 파일 동기화 포함
rsync -avz --delete -e "ssh -p 22001" local_folder/ developer@server.company.com:/workspace/

# 진행 상황 표시
rsync -avz --progress -e "ssh -p 22001" large_file.zip developer@server.company.com:/workspace/

# dry-run (실제 전송 없이 확인)
rsync -avzn -e "ssh -p 22001" local_folder/ developer@server.company.com:/workspace/
```

### 3.4 FileZilla (GUI 클라이언트)

GUI를 선호하는 경우 FileZilla 사용:

1. **FileZilla 설치**: https://filezilla-project.org/
2. **사이트 관리자** 열기 (Ctrl+S)
3. **새 사이트** 추가:
   - 프로토콜: SFTP
   - 호스트: server.company.com
   - 포트: 22001
   - 사용자: developer
   - 로그온 유형: 키 파일 또는 비밀번호
4. **연결** 후 드래그 앤 드롭으로 파일 전송

---

## 4. 오프라인 패키지 설치

### 4.1 Python 패키지 (pip)

**외부 PC에서 패키지 다운로드:**

```bash
# 패키지 다운로드 (인터넷 가능한 PC)
pip download -d ./packages -r requirements.txt

# 특정 패키지만
pip download -d ./packages numpy pandas scikit-learn
```

**워크스페이스에서 오프라인 설치:**

```bash
# 패키지 폴더 업로드 후
pip install --no-index --find-links=./packages -r requirements.txt

# 또는 개별 설치
pip install --no-index --find-links=./packages numpy
```

### 4.2 Node.js 패키지 (npm/pnpm)

**외부 PC에서 node_modules 패키징:**

```bash
# 패키지 설치
npm install

# node_modules 압축
tar -czvf node_modules.tar.gz node_modules/
# 또는
zip -r node_modules.zip node_modules/
```

**워크스페이스에서:**

```bash
# 압축 해제
tar -xzvf node_modules.tar.gz
# 또는
unzip node_modules.zip

# 심볼릭 링크 재생성 (필요시)
npm rebuild
```

### 4.3 Java 패키지 (Maven)

**외부 PC에서 의존성 다운로드:**

```bash
# 의존성 다운로드
mvn dependency:go-offline

# 로컬 저장소 패키징
tar -czvf maven-repo.tar.gz ~/.m2/repository/
```

**워크스페이스에서:**

```bash
# 압축 해제
tar -xzvf maven-repo.tar.gz -C ~/

# 오프라인 빌드
mvn install -o  # -o: offline mode
```

### 4.4 Go 모듈

**외부 PC에서:**

```bash
# 모듈 다운로드
go mod download

# vendor 디렉토리 생성
go mod vendor

# vendor 압축
zip -r vendor.zip vendor/
```

**워크스페이스에서:**

```bash
# vendor 압축 해제
unzip vendor.zip

# vendor 모드로 빌드
go build -mod=vendor
```

---

## 5. 사내 패키지 저장소 설정

### 5.1 Python (pip) - PyPI 미러

**환경 변수 설정:**

```bash
# ~/.pip/pip.conf 또는 환경변수
export PIP_INDEX_URL=http://internal-pypi.company.com/simple/
export PIP_TRUSTED_HOST=internal-pypi.company.com
```

**pip.conf:**

```ini
[global]
index-url = http://internal-pypi.company.com/simple/
trusted-host = internal-pypi.company.com
```

### 5.2 Node.js (npm) - npm 미러

**.npmrc 설정:**

```
registry=http://internal-npm.company.com/
strict-ssl=false
```

**환경 변수:**

```bash
export NPM_CONFIG_REGISTRY=http://internal-npm.company.com/
```

### 5.3 Java (Maven) - Nexus/Artifactory

**settings.xml 설정:**

```xml
<settings>
  <mirrors>
    <mirror>
      <id>company-maven</id>
      <url>http://internal-maven.company.com/repository/maven-public/</url>
      <mirrorOf>*</mirrorOf>
    </mirror>
  </mirrors>
</settings>
```

---

## 6. 자동화 스크립트 예시

### 6.1 배포 스크립트 (deploy.sh)

```bash
#!/bin/bash
# 프로젝트 배포 스크립트

WORKSPACE_ID="ws_myproject"
SSH_HOST="server.company.com"
SSH_PORT="22001"
SSH_USER="developer"

# 프로젝트 압축
tar -czvf project.tar.gz \
  --exclude=node_modules \
  --exclude=.git \
  --exclude=__pycache__ \
  .

# 업로드
scp -P $SSH_PORT project.tar.gz $SSH_USER@$SSH_HOST:/workspace/

# 원격 실행
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST << 'EOF'
cd /workspace
tar -xzvf project.tar.gz
rm project.tar.gz
# 의존성 설치 (오프라인 모드)
pip install -r requirements.txt --no-index --find-links=./packages
EOF

echo "배포 완료!"
```

### 6.2 패키지 동기화 스크립트 (sync-packages.sh)

```bash
#!/bin/bash
# 오프라인 패키지 동기화

SSH_HOST="server.company.com"
SSH_PORT="22001"

# Python 패키지 동기화
rsync -avz --progress \
  -e "ssh -p $SSH_PORT" \
  ./packages/ \
  developer@$SSH_HOST:/workspace/packages/

# Node 패키지 동기화
rsync -avz --progress \
  -e "ssh -p $SSH_PORT" \
  ./node_modules/ \
  developer@$SSH_HOST:/workspace/node_modules/
```

---

## 7. 문제 해결

### Q: 파일 업로드가 너무 느립니다

- **해결**: ZIP 압축 후 업로드, 또는 rsync 사용
- rsync는 이미 존재하는 파일을 건너뛰어 빠름

### Q: SSH 연결이 자주 끊깁니다

**SSH 설정 추가 (~/.ssh/config):**

```
Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
```

### Q: 대용량 파일 업로드 실패

- 웹 UI: 100MB 제한 → SCP/rsync 사용
- ZIP: 500MB 제한 → 분할 압축 또는 rsync 사용

### Q: 권한 오류 발생

```bash
# 워크스페이스 내에서
sudo chown -R developer:developer /workspace
chmod -R 755 /workspace
```

---

## 8. 참고 자료

- [OpenSSH SCP](https://man.openbsd.org/scp)
- [rsync 매뉴얼](https://rsync.samba.org/documentation.html)
- [pip 오프라인 설치](https://pip.pypa.io/en/stable/user_guide/#installing-from-local-packages)
- [npm 오프라인 모드](https://docs.npmjs.com/cli/v10/using-npm/config#offline)
