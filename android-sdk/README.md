# android-sdk (Offline Android SDK)

목적: IDE 컨테이너에서 `apt-get`이 막힌 환경에서도 Android 앱 개발(빌드/adb/gradle)을 가능하게 하기 위해,
Android SDK를 **오프라인으로 준비**하여 IDE 컨테이너에 마운트합니다.

## 권장 배치

- 이 폴더(`android-sdk/`) 아래에 Android SDK를 “이미 설치/추출된 형태”로 배치합니다.
- 최소 구성(권장):
  - `platform-tools/` (adb 포함)
  - `cmdline-tools/latest/bin/` (sdkmanager 포함)
  - `build-tools/<version>/`
  - `platforms/android-<api>/`

## 동작 방식

- API가 IDE 컨테이너 생성 시 이 폴더를 `/opt/android-sdk`로 ro 마운트합니다.
- IDE 컨테이너 entrypoint가 `/opt/android-sdk`를 감지하면:
  - `ANDROID_HOME`, `ANDROID_SDK_ROOT`를 설정
  - `platform-tools`, `cmdline-tools`를 PATH에 추가합니다.

## 설정

`docker-compose.yml`의 `api` 서비스 환경변수:

- `HOST_ANDROID_SDK_PATH=/home/ubuntu/projects/cursor-onprem-poc/android-sdk`

## 주의사항

- Android SDK는 용량이 크므로 Git에 커밋하지 않도록 `.gitignore` 처리되어 있습니다.
- 오프라인 환경에서는 SDK 라이선스/승인 절차가 별도로 필요할 수 있습니다.

