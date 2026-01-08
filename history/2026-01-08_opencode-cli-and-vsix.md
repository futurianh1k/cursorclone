# 변경 내역: OpenCode VSIX + CLI(오프라인) 기본 탑재 지원 (2026-01-08)

## 요청자(사용자) 요구사항 요약

- OpenCode VSIX는 Open VSX에서 다운로드 가능하며, CLI(opencode.ai)가 설치되어야 정상 동작한다고 함
- Copilot처럼 쓰려면 별도 GUI가 필요한지 질문
- 온프레미스 IDE(code-server)에서 워크스페이스 생성/IDE 시작 시 기본 탑재를 원함

## Assistant(제가) 응답 내용(무엇을 할지)

- 별도의 독립 GUI가 필수인 것은 아니며, 보통 VS Code 확장(UI)+CLI(백엔드)로 IDE 내에서 사용 가능하다고 안내
- 오프라인 환경에서 VSIX/CLI를 host에 배치해 IDE 컨테이너 시작 시 자동 설치/탑재되도록 구현

## 실제로 수행한 변경 내용(파일/설계 요약)

- `apps/api/src/services/ide_service.py`
  - `HOST_OPENCODE_CLI_PATH`가 설정되면 IDE 컨테이너에 `/opt/opencode-cli`로 ro 마운트
- `docker/code-server/entrypoint.sh`
  - `/opt/opencode-cli/opencode` 감지 시 PATH에 추가
- `docker-compose.yml`
  - `HOST_OPENCODE_CLI_PATH` 기본값 추가
- `.gitignore`, `opencode-cli/README.md`
  - CLI 바이너리 커밋 방지/운영 가이드
- 문서:
  - `docs/0023-opencode-extension-and-cli.md` 추가(개념/구성 가이드)
- 테스트:
  - `apps/api/tests/test_ide_opencode_cli_mount.py` 추가

## 테스트 및 검증 방법

```bash
cd /home/ubuntu/projects/cursor-onprem-poc/apps/api
pytest -q tests/test_ide_opencode_cli_mount.py
```

IDE 컨테이너 마운트 확인:
```bash
docker inspect <ide-container> --format '{{json .HostConfig.Binds}}' | python -m json.tool
```

## 향후 작업 제안 또는 주의사항

- Open VSX 접근이 불가한 환경에서는 VSIX를 내부 반입(승인/검증) 후 `ide-extensions/`에 배치하세요.
- CLI 인증(로그인/토큰) 방식에 따라 추가 환경변수/설정 주입이 필요할 수 있습니다(확장 문서에 맞춰 조정).

