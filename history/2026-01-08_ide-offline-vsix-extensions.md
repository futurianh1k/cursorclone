# 변경 내역: IDE 오프라인 VSIX 확장(예: opencode agent) 기본 탑재 (2026-01-08)

## 요청자(사용자) 요구사항 요약

- 현재 컨테이너에 opencode ai agent가 설치되지 않은 것 같다.
- 워크스페이스 생성/IDE 구동 시 기본 에이전트로 opencode를 탑재한 상태에서 시작할 수 있는가?

## Assistant(제가) 응답 내용(무엇을 할지)

- 외부 다운로드 없이(온프레미스/VDE) VSIX 파일을 통해 IDE 확장을 기본 탑재할 수 있도록,
  IDE 컨테이너 시작 시 자동 설치 + host extensions 폴더 마운트 방식을 구현한다.

## 실제로 수행한 변경 내용(파일/설계 요약)

- `docker/code-server/entrypoint.sh`
  - `/opt/extra-extensions/*.vsix` 자동 설치(실패해도 IDE 스타트는 계속)
- `docker/code-server/Dockerfile`
  - wrapper 엔트리포인트로 전환(오프라인 VSIX 자동 설치 지원)
- `apps/api/src/services/ide_service.py`
  - `HOST_IDE_EXTENSIONS_PATH`가 설정된 경우, IDE 컨테이너에 `/opt/extra-extensions`로 ro 마운트
- `docker-compose.yml`
  - `api` 서비스에 `HOST_IDE_EXTENSIONS_PATH` 환경변수 기본값 추가
- `ide-extensions/README.md`, `.gitignore`
  - VSIX를 Git에 커밋하지 않도록 가이드/ignore 추가
- `apps/api/tests/test_ide_offline_extensions.py`
  - 추가 확장 마운트 로직(볼륨 merge 형태) 최소 단위 테스트 추가
- 문서:
  - `docs/0022-ide-offline-vsix-extensions.md` 추가
  - `docs/0018-solution-user-manual.md`에 관련 문구 추가

## 테스트 및 검증 방법

```bash
cd /home/ubuntu/projects/cursor-onprem-poc/apps/api
pytest -q tests/test_ide_offline_extensions.py
```

IDE 마운트 확인(예):
```bash
docker inspect <ide-container> --format '{{json .HostConfig.Binds}}' | python -m json.tool
```

## 향후 작업 제안 또는 주의사항

- 완전 오프라인 빌드(VDE)에서는 Tabby/Continue도 마켓플레이스 다운로드 대신 VSIX 공급 방식으로 전환하는 것이 필요합니다.

