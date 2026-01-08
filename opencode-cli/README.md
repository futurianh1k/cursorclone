# opencode-cli (Offline CLI)

목적: `opencode.ai` CLI를 외부 다운로드 없이(온프레미스/VDE) code-server IDE 컨테이너에 기본 탑재하기 위한 폴더입니다.

## 기대하는 파일 배치

- `opencode-cli/opencode` (실행 파일)

> 파일명은 `opencode`를 권장합니다(확장이 일반적으로 이 이름을 호출할 가능성이 높음).

## 동작 방식(요약)

- API가 IDE 컨테이너를 생성할 때 이 폴더를 IDE 컨테이너에 `/opt/opencode-cli`로 ro 마운트합니다.
- IDE 컨테이너 시작 시 엔트리포인트가 `/opt/opencode-cli/opencode`를 감지하면 PATH에 추가합니다.
- 이후 VS Code 확장(opencode VSIX)이 내부적으로 `opencode` CLI를 호출할 수 있습니다.

## 설정

`docker-compose.yml`의 `api` 서비스 환경변수:

- `HOST_OPENCODE_CLI_PATH=/home/ubuntu/projects/cursor-onprem-poc/opencode-cli`

## 주의사항

- 바이너리/실행파일은 Git에 커밋하지 않는 것을 권장합니다(`.gitignore` 처리됨).

