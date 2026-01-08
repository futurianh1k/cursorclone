# 변경 내역: 무거운 code-server 이미지(오프라인 toolchain 포함) 옵션 추가 (2026-01-08)

## 요청자(사용자) 요구사항 요약

- “무거운 code-server 이미지 만드는 버전”을 레포에 추가해달라.

## Assistant(제가) 응답 내용(무엇을 할지)

- `offline/debs/`에 준비된 `.deb` 번들을 기반으로 오프라인에서도 빌드 가능한 `Dockerfile.heavy`를 추가한다.
- docker-compose에 heavy 빌더 서비스를 추가하고, `IDE_CONTAINER_IMAGE` 전환 방법을 문서화한다.
- 최소 1개 테스트를 추가한다.

## 실제로 수행한 변경 내용(파일/설계 요약)

- `docker/code-server/Dockerfile.heavy` 추가
  - `offline/debs/*.deb`를 COPY 후 `dpkg -i`로 설치(의존성 포함 번들 필요)
  - 기존 entrypoint/기본 설정/확장 설치 흐름 유지
- `docker-compose.yml` 변경
  - `code-server-builder-heavy` 서비스 추가
  - 결과 이미지: `cursor-poc-code-server-heavy:latest`
- 문서:
  - `docs/0028-code-server-heavy-image.md` 추가(준비/빌드/전환/검증)
  - `docs/0028-session-notes.md` 추가(요약+해시)
- 테스트:
  - `apps/api/tests/test_code_server_heavy_artifacts.py` 추가(산출물 존재 확인)

## 테스트 및 검증 방법

```bash
cd /home/ubuntu/projects/cursor-onprem-poc/apps/api
pytest -q tests/test_code_server_heavy_artifacts.py
```

## 향후 작업 제안 또는 주의사항

- 완전 오프라인 빌드를 위해서는 `offline/debs`에 **의존성까지 포함한** deb closure가 필요합니다.
- 필요 패키지 목록은 `docs/0026-offline-toolchain-plan.md`를 기준으로 확정/버전 고정을 권장합니다.

