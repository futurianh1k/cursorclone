# 0027 - 대화/작업 기록(요약 + 해시)

> 보안 원칙: 프롬프트/응답 원문을 저장하지 않습니다. 필요 시 **해시 + 메타데이터**만 기록합니다.

## 사용자 요청(요약)

- 금융권 주요 언어/도구에 대해 “무엇을 VSIX로 준비할지 / 무엇을 Ubuntu .deb로 준비할지” 정리
- IDE 런타임에서 `apt-get`이 막힌 환경을 전제로, 오프라인 번들 전략 필요
- Android 앱 개발 준비 포함
- opencode VSIX는 `ide-extensions/`에 이미 배치 완료

## 사용자 요청 원문 해시

- sha256: `457299e66e5af143d25c2d98c38a20c9ca2d96b7b9fa34f3fcf34f20965690e1`

## Assistant가 수행한 작업(요약)

- `docs/0026-offline-toolchain-plan.md`: VSIX vs deb vs 오프라인 SDK/바이너리 구분 및 준비 계획 문서화
- Android SDK 오프라인 마운트 지원 추가(`HOST_ANDROID_SDK_PATH`, `/opt/android-sdk`)
- 오프라인 deb 번들 폴더(`offline/debs/`) 및 `.gitignore` 규칙 추가
- opencode VSIX 자동 설치 동작(IDE 컨테이너 entrypoint) 로그로 검증

