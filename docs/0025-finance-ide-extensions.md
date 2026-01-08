# 0025 - 금융권 온프레미스 IDE(code-server) 권장 확장(VSIX) & 오프라인 준비 가이드

전제:
- IDE 컨테이너 내부에서 `sudo apt-get install` 같은 **런타임 패키지 설치가 차단**됨
- 외부 네트워크가 제한될 수 있음(VDE/망분리)
- 따라서 “IDE 경험”은 **VSIX 사전 준비 + 이미지 빌드 시점의 시스템 도구 포함**으로 구성해야 함

---

## 1) 무엇을 VSIX로 준비해야 하나? (권장 목록)

> 원칙: “언어 지원 + 포맷/린트 + 설정 파일(인프라) + 문서 포맷(OpenAPI/Proto) + 생산성”을 최소 세트로 잡습니다.

### A. 공통(거의 모든 팀)

- **GitLens**: Git 변경/블레임/히스토리 생산성
- **EditorConfig**: 팀 코딩 스타일 강제
- **YAML**: k8s/CI/설정 파일 편집
- **JSON**: JSON schema 기반 편집 도움
- **Markdown**: Runbook/ADR 문서 품질

### B. Python(금융권 배치/ETL/모델/자동화)

- **Python**(ms-python.python)
- **Pylance**(ms-python.vscode-pylance) *(오프라인에서는 동작 방식 확인 필요: 일부 구성은 추가 다운로드가 개입될 수 있음)*
- **Ruff** 또는 **Flake8** 계열 확장(팀 표준에 맞춰 1개로 통일 권장)

### C. Java/Spring(금융권 핵심 시스템)

- **Extension Pack for Java**(vscjava.vscode-java-pack) 또는 구성 요소(필요한 것만)
- **Spring Boot Tools**(Pivotal/vmware 계열)

> 주의: Java는 “확장”만으로 끝나지 않고, 보통 **JDK(시스템 도구)** 가 필요합니다.

### D. Go

- **Go**(golang.Go)

> 주의: `gopls`가 필요한 경우가 많고, 환경에 따라 확장이 다운로드를 시도할 수 있어 오프라인 검증이 필요합니다.

### E. C/C++ (레거시/성능 모듈)

- **C/C++**(ms-vscode.cpptools)

> 주의: 디버깅/빌드에는 `gdb/clang/gcc/make` 같은 **시스템 패키지**가 필요할 수 있습니다.

### F. .NET

- **C#**(ms-dotnettools.csharp)

> 주의: `dotnet` 런타임/SDK는 보통 시스템 도구로 포함해야 합니다.

### G. 데이터/SQL(금융권 필수)

- **SQL 관련 확장**(예: SQL Formatter, SQLTools 등 팀 표준 1개)
- **PostgreSQL**/**Oracle**/**MSSQL** 등 DB별 도구는 “네트워크 정책”과 “계정 정책”을 함께 고려

### H. 인프라/운영(금융권 DevSecOps)

- **Docker**(ms-azuretools.vscode-docker) *(단, IDE 컨테이너에 docker daemon이 없으면 UI만 제공될 수 있음)*
- **Kubernetes**(ms-kubernetes-tools.vscode-kubernetes-tools)
- **Terraform**(hashicorp.terraform)
- **Ansible**(redhat.ansible)

### I. API/문서/스키마

- **OpenAPI/Swagger Viewer**(팀 표준 선택)
- **Proto3**(protobuf 편집)

---

## 2) “VSIX만 있으면 끝”이 아닌 경우(중요)

확장은 UI/편집기 기능을 제공하지만, 실제로는 아래가 필요할 수 있습니다.

- **언어 런타임/SDK**: JDK, dotnet SDK, Go toolchain, Python 패키지 등
- **빌드 도구**: make, gcc/clang, cmake
- **디버거**: gdb/lldb
- **기본 유틸**: git, ssh, curl, jq, ripgrep, unzip

이런 것들은 IDE 컨테이너에서 `apt-get`이 막혀 있으면 **사전에 이미지에 포함**해야 합니다.

---

## 3) 오프라인/VDE에서 “deb를 미리 준비해야 하나?”

### 결론

- **IDE 컨테이너 런타임에서 설치가 막혀 있다면**: 네, “어떤 방식으로든” 사전 준비가 필요합니다.
  - 가장 권장: **이미지 빌드 시점에 apt로 설치**
  - 빌드도 오프라인이면: **.deb를 미리 확보**하거나 내부 **apt 미러/리포지토리**가 필요

### 권장 전략(우선순위)

1) **빌드 시점 설치(가장 단순)**
   - `docker/code-server/Dockerfile`에서 `apt-get install`로 필요한 패키지를 이미지에 포함
2) **완전 오프라인 빌드**
   - 내부 반입한 `.deb`를 Docker build 컨텍스트에 두고 `dpkg -i`로 설치
   - 또는 내부 apt mirror를 운영(보안 승인/검증 프로세스 포함)
3) **“도구 설치를 IDE에서 하지 않는 운영 모델”**
   - 빌드/배포/스캔은 CI(내부)에서 수행하고, IDE는 편집/리뷰 중심으로 유지

---

## 4) Docker는 IDE 컨테이너에 꼭 필요한가?

대부분의 금융권 운영 모델에서는 **IDE 컨테이너에 docker daemon을 넣는 건 권장하지 않습니다**.

- docker.sock을 IDE 컨테이너에 마운트하면 권한 상승/탈출 위험이 커집니다.
- 대신 “이미 이 레포가 하고 있는 방식”처럼:
  - **API(서버)가 docker를 제어**하고
  - 사용자 IDE는 제한된 기능만 사용하도록 하는 것이 안전합니다.

다만 팀 요구가 “IDE에서 docker build를 직접 해야 한다”라면:
- 별도의 안전한 빌드 런너(격리된 builder)나 내부 CI를 권장합니다.

---

## 5) 운영 체크리스트(추천)

- VSIX는 `ide-extensions/`에 보관(바이너리는 Git에 커밋하지 않음)
- CLI/런타임 바이너리는 별도 폴더로 오프라인 마운트(예: `opencode-cli/`)
- “새 워크스페이스 생성 시 기본 탑재” 검증:
  - IDE 컨테이너 마운트 확인(`/opt/extra-extensions`)
  - IDE 로그에서 VSIX 설치 로그 확인

