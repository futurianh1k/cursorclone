# offline/debs

목적: IDE(code-server) 이미지를 **오프라인으로 빌드**해야 하는 환경에서, 필요한 Ubuntu 패키지(.deb)를 사전에 반입/준비하기 위한 폴더입니다.

## 사용 원칙

- 이 폴더에는 `.deb` 파일을 두되, **Git에는 커밋하지 않습니다**(바이너리/라이선스/용량 이슈).
- deb는 **의존성까지 포함하여** 준비해야 `dpkg -i`로 설치가 가능합니다.

## 권장 후보(예시)

- 기본 유틸: git, openssh-client, curl, jq, ripgrep, unzip, ca-certificates
- 빌드/디버그: build-essential, gdb, cmake, pkg-config
- 언어/SDK: openjdk-17-jdk, dotnet-sdk-*, golang-go(또는 go tar)

