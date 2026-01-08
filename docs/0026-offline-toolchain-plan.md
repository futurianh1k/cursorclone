# 0026 - 금융권 On-Prem IDE 오프라인 번들(Extension/Toolchain) 준비 계획

요구사항(사용자 제공):
- 언어: Java/Spring, C/C++, Python, .NET, Node/React/TypeScript/Next.js, Go
- 컨테이너/배포: Kubernetes, Docker, Terraform, Ansible
- DB: MySQL, PostgreSQL, MongoDB
- 도구: GitLens, Markdown to PDF, PDF Reader, Office Reader
- IDE 컨테이너 런타임에서 `apt-get` 불가(다운로드 차단)
- 빌드도 오프라인으로 수행해야 함

---

## 1) 무엇을 VSIX로 준비할까?

### 1-1. 언어/프론트엔드

- Java: `vscjava.vscode-java-pack`(또는 필요한 하위 구성만)
- Spring: `vmware.vscode-spring-boot`(+ 필요 시 `vmware.vscode-spring-initializr`)
- C/C++: `ms-vscode.cpptools`
- Python: `ms-python.python`
- .NET/C#: `ms-dotnettools.csharp`
- Go: `golang.Go`
- Node/TS: `dbaeumer.vscode-eslint`, `esbenp.prettier-vscode`, `ms-vscode.vscode-typescript-next`(선택)

### 1-2. DevSecOps/Infra

- Kubernetes: `ms-kubernetes-tools.vscode-kubernetes-tools`
- Terraform: `hashicorp.terraform`
- Ansible: `redhat.ansible`
- Docker(클라이언트 UI): `ms-azuretools.vscode-docker` *(daemon이 없으면 UI만 동작할 수 있음)*

### 1-3. DB/데이터

- SQL: 팀 표준 1개(예: SQL Formatter/SQLTools 계열)
- MongoDB: MongoDB 확장(팀 표준 선택)

### 1-4. 문서/리더

- GitLens: `eamodio.gitlens`
- Markdown PDF: `yzane.markdown-pdf`
- PDF Viewer: `tomoki1207.pdf`
- Office Viewer: (Open VSX에서 제공되는 항목 중 팀 표준 선택)

> 주의: 확장별로 Open VSX 제공 여부/버전이 다를 수 있으니 “표준 리스트를 확정”한 뒤 VSIX를 확보하세요.

---

## 2) 무엇을 Ubuntu .deb(또는 이미지 빌드 시점 설치)로 준비할까?

원칙:
- 확장이 언어서버/디버거/빌드 도구를 요구하면 **VSIX만으로 부족**합니다.
- 런타임 설치가 막혀 있으니, **이미지에 포함**하거나 **오프라인 바이너리 마운트**가 필요합니다.

### 2-1. 기본 유틸(권장 deb)

- `git`
- `openssh-client`
- `curl`
- `jq`
- `ripgrep`
- `unzip`
- `ca-certificates`
- `bash`, `coreutils` *(보통 베이스 이미지에 있음)*

### 2-2. 빌드/디버그(권장 deb)

- `build-essential`(gcc/g++/make)
- `gdb`
- `cmake`
- `pkg-config`

### 2-3. 언어 런타임/SDK(환경별)

- JDK(권장): `openjdk-17-jdk` 또는 조직 표준 JDK
- .NET SDK: `dotnet-sdk-*` *(기본 Ubuntu repo가 아닌 경우가 많아 오프라인 deb 확보 필요)*
- Go toolchain: `golang-go` *(또는 go 공식 tarball을 오프라인으로 준비하여 마운트)*

### 2-4. 컨테이너/클러스터 도구

- docker **daemon**은 IDE 컨테이너에 두지 않는 것을 권장(보안)
- docker **cli**, `kubectl`, `helm`, `terraform` 등은:
  - (A) deb로 이미지에 포함하거나
  - (B) 오프라인 바이너리 tar를 `/opt/tools` 같은 경로로 마운트하는 방식 권장

---

## 3) Android 앱 개발(오프라인) 준비

Android는 “VSIX”보다 “SDK/빌드툴” 비중이 큽니다.

- Android SDK(오프라인): `android-sdk/`에 설치/추출된 SDK를 준비하고,
  IDE 컨테이너에 `/opt/android-sdk`로 마운트
- (선택) JDK: Android Gradle Plugin 버전에 맞는 JDK 포함 필요

> 이 레포는 `HOST_ANDROID_SDK_PATH`를 통해 Android SDK 마운트를 지원합니다.

---

## 4) 오프라인 번들 폴더 구조(권장)

- `ide-extensions/` : IDE 시작 시 자동 설치되는 VSIX(이미 구현)
- `opencode-cli/` : opencode 실행 파일(이미 구현)
- `android-sdk/` : Android SDK(마운트 지원 추가됨)
- (선택) `offline/debs/` : 오프라인 deb 번들(빌드 컨텍스트에 포함)
- (선택) `offline/tools/` : kubectl/helm/terraform 등 바이너리 번들

---

## 5) 다음 단계(권장)

1) “표준 VSIX 리스트”를 확정하고 Open VSX에서 VSIX를 확보(버전 고정)
2) 오프라인 deb 번들(의존성 포함)을 준비(내부 반입 프로세스 포함)
3) code-server “heavy toolchain” 이미지(Dockerfile variant)로 한 번에 번들링

