# 0028 - "Heavy" code-server 이미지(오프라인 툴체인 포함) 만들기/사용하기

목표:
- IDE 컨테이너에서 `apt-get`이 막힌 환경에서도 개발이 가능하도록
- **시스템 도구/SDK를 포함한 “무거운 code-server 이미지”** 를 빌드/사용합니다.

---

## 1) 언제 heavy 이미지가 필요한가?

- IDE 컨테이너에서 패키지 설치가 차단됨(`apt-get` 불가)
- 빌드도 오프라인(외부 apt repo 접근 불가)
- 언어/디버깅/빌드 도구가 IDE 컨테이너 내부에 필요함

---

## 2) 구성 요소

- Dockerfile: `docker/code-server/Dockerfile.heavy`
- deb 번들 폴더: `offline/debs/` (Git 커밋 금지)
- 이미지 태그: `cursor-poc-code-server-heavy:latest`

---

## 3) 오프라인 deb 번들 준비

`offline/debs/`에 **의존성까지 포함한** `.deb`들을 넣어야 합니다.

권장 후보(예시):
- 기본 유틸: `git`, `openssh-client`, `curl`, `jq`, `ripgrep`, `unzip`, `ca-certificates`
- 빌드/디버그: `build-essential`, `gdb`, `cmake`, `pkg-config`
- 언어 SDK: `openjdk-17-jdk`(또는 표준), `dotnet-sdk-*`, `golang-go`(또는 go tarball 기반 대체)

> 중요: `Dockerfile.heavy`는 외부 repo 의존을 피하기 위해 `dpkg -i`로만 설치합니다.  
> 따라서 의존성이 누락되면 빌드가 실패합니다(의도된 동작).

---

## 4) heavy 이미지 빌드

```bash
cd /home/ubuntu/projects/cursor-onprem-poc
docker compose build code-server-builder-heavy
```

---

## 5) IDE에서 heavy 이미지 사용(전환)

1) `docker-compose.yml` 또는 `.env`에서 API 환경변수 변경:
- `IDE_CONTAINER_IMAGE=cursor-poc-code-server-heavy:latest`

2) API 재기동(권장: env 반영 위해 recreate):

```bash
docker compose up -d --no-deps --force-recreate api
```

3) 기존 IDE 컨테이너는 “이미 만들어진 이미지”를 계속 쓰므로,
   워크스페이스 IDE 컨테이너를 재생성해야 합니다.

---

## 6) 함께 쓰면 좋은 것(오프라인 VSIX/CLI/Android)

- VSIX 자동 설치: `ide-extensions/*.vsix` (IDE 시작 시 자동 설치)
- opencode CLI 마운트: `opencode-cli/opencode`
- Android SDK 마운트: `android-sdk/` → `/opt/android-sdk`

관련 문서:
- `docs/0022-ide-offline-vsix-extensions.md`
- `docs/0023-opencode-extension-and-cli.md`

