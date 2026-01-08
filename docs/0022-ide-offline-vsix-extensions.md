# 0022 - IDE에 오프라인 VSIX 확장(예: opencode agent) 기본 탑재하기

목표: 워크스페이스 생성/IDE 구동 시, code-server 안에 **추가 에이전트(확장)를 기본으로 탑재**해서 시작합니다.  
제약: 외부 다운로드 없이(온프레미스/VDE) 동작해야 합니다.

---

## 동작 방식(요약)

- 운영자가 docker host의 `ide-extensions/` 폴더에 **VSIX 파일**을 넣어둡니다.
- API가 IDE 컨테이너를 생성할 때, 해당 폴더를 IDE 컨테이너에 **`/opt/extra-extensions`로 read-only 마운트**합니다.
- IDE 컨테이너 시작 시 엔트리포인트가 `/opt/extra-extensions/*.vsix`를 자동으로 설치합니다.

---

## 1) 준비: VSIX 파일 배치

1) docker host에서 아래 폴더를 확인합니다.

- `ide-extensions/` (레포 루트)

2) opencode 에이전트 VSIX를 이 폴더에 복사합니다.

- 예: `ide-extensions/opencode-agent.vsix`

> 주의: VSIX는 바이너리이므로 Git에 커밋하지 않도록 `.gitignore`에 포함되어 있습니다.

---

## 2) 설정: API가 확장 폴더를 IDE에 마운트하도록

`docker-compose.yml`의 `api` 서비스에 아래 환경변수가 설정되어 있어야 합니다.

- `HOST_IDE_EXTENSIONS_PATH=/home/ubuntu/projects/cursor-onprem-poc/ide-extensions`

기본값으로 이미 들어가 있으며, 환경에 따라 절대 경로만 맞게 조정하면 됩니다.

---

## 3) 적용: IDE 재생성(또는 재시작)

권장(이미지/설정 반영):

```bash
cd /home/ubuntu/projects/cursor-onprem-poc
docker compose build code-server-builder
docker compose up -d --no-deps --force-recreate api
```

그 다음:
- 기존 IDE 컨테이너를 지우고(또는 워크스페이스에서 재시작),
- 워크스페이스의 IDE URL을 다시 조회/열면 새 컨테이너가 생성됩니다.

---

## 4) 확인 방법

- IDE 컨테이너 bind에 아래가 포함되는지 확인:
  - `<host>/ide-extensions:/opt/extra-extensions:ro`
- IDE 컨테이너 로그에서 “Installing VSIX extension” 로그가 보이는지 확인

---

## 참고/주의사항

- 현재 `docker/code-server/Dockerfile`은 Tabby/Continue 등을 마켓플레이스에서 설치합니다.
  완전 오프라인(VDE) 빌드를 목표로 한다면 Tabby/Continue도 VSIX로 공급하는 방식으로 추가 정리가 필요합니다.

