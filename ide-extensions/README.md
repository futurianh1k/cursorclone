# ide-extensions (Offline VSIX)

목적: 외부 네트워크 없이(온프레미스/VDE) code-server IDE에 **추가 VS Code 확장(VSIX)** 을 “기본 탑재”하기 위한 폴더입니다.

## 사용 방법(권장)

1) 이 폴더에 **VSIX 파일**을 복사합니다. (예: `opencode-agent.vsix`)

2) API 컨테이너가 IDE 컨테이너를 생성할 때 이 폴더를 read-only로 마운트하도록,
아래 환경변수를 **docker-compose.yml의 api 서비스**에 설정합니다.

- `HOST_IDE_EXTENSIONS_PATH=/home/ubuntu/projects/cursor-onprem-poc/ide-extensions`

3) 워크스페이스를 새로 만들거나, 기존 IDE 컨테이너를 재시작하면,
IDE 컨테이너 시작 시 `/opt/extra-extensions/*.vsix`를 자동 설치합니다.

## 주의사항(보안/운영)

- VSIX는 바이너리이므로 **Git에 커밋하지 않는 것을 권장**합니다.
- VSIX 내부에 민감 설정이 포함되지 않도록 주의하세요.

