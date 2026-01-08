# 변경 내역: 금융권 IDE 오프라인 툴체인(확장/도구) + Android SDK 마운트 (2026-01-08)

## 요청자(사용자) 요구사항 요약

- Java/Spring, C/C++, Python, .NET, Node/React/TS/Next, Go 등 주요 언어용 확장 필요
- Kubernetes/Docker/Terraform/Ansible, MySQL/PostgreSQL/MongoDB, 문서/리더 도구 확장 필요
- IDE 컨테이너 런타임에서 apt 설치가 막혀 있고, 빌드도 오프라인이어야 함
- Android 앱 개발 준비 포함
- opencode VSIX는 `ide-extensions/`에 배치함

## Assistant(제가) 응답 내용(무엇을 할지)

- 무엇을 VSIX로 준비할지 / 무엇을 deb(또는 오프라인 SDK/바이너리)로 준비할지 분류해 문서화
- 오프라인 환경에서도 IDE가 Android 개발에 필요한 SDK 경로를 인지할 수 있도록 마운트 지원 추가
- opencode VSIX 자동 설치 동작을 로그로 검증

## 실제로 수행한 변경 내용(파일/설계 요약)

- `docs/0026-offline-toolchain-plan.md`
  - 금융권 표준 스택 기준 VSIX vs deb vs SDK/바이너리 구분 및 준비 전략 문서화
- `offline/debs/README.md`, `.gitignore`
  - 오프라인 deb 번들 구조 추가 및 deb 커밋 방지
- Android SDK 오프라인 마운트 지원
  - `apps/api/src/services/ide_service.py`: `HOST_ANDROID_SDK_PATH` → IDE 컨테이너 `/opt/android-sdk` ro 마운트
  - `docker/code-server/entrypoint.sh`: ANDROID_HOME/SDK_ROOT 설정 + PATH 보강
  - `android-sdk/README.md`, `.gitignore`: 오프라인 SDK 가이드/커밋 방지
  - `apps/api/tests/test_ide_android_sdk_mount.py`: 단위 테스트 추가

## 테스트 및 검증 방법

```bash
cd /home/ubuntu/projects/cursor-onprem-poc/apps/api
pytest -q tests/test_ide_android_sdk_mount.py
```

opencode VSIX 자동 설치 로그 확인(예):
```bash
docker logs <ide-container> | grep "Installing VSIX"
```

## 향후 작업 제안 또는 주의사항

- 완전 오프라인 “heavy toolchain 이미지”를 만들려면 `.deb` 의존성까지 포함한 번들이 필요합니다.
- docker daemon을 IDE 컨테이너에 넣는 것은 보안상 권장하지 않으며, 빌드/배포는 별도 러너(내부 CI)로 분리 권장합니다.

