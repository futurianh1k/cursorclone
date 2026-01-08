# 0022 - 대화/작업 기록(요약 + 해시)

> 보안 원칙: 프롬프트/응답 원문을 저장하지 않습니다. 필요 시 **해시 + 메타데이터**만 기록합니다.

## 사용자 요청(요약)

- 워크스페이스 생성/IDE 구동 시 기본 에이전트로 opencode를 탑재한 상태로 시작할 수 있는지 확인 및 구현

## 사용자 요청 원문 해시

- sha256: `71d0bb16b7aa3d89d1ccadd48ddd9967cafb71c8b0560d3bb0bc717d90c42e59`

## Assistant가 수행한 작업(요약)

- code-server 컨테이너 시작 시 `/opt/extra-extensions/*.vsix`를 자동 설치하는 엔트리포인트 추가
- API가 IDE 컨테이너 생성 시 host의 `ide-extensions/` 폴더를 `/opt/extra-extensions`로 마운트하도록 개선
- 운영 문서/가이드(`docs/0022-...`) 추가 및 테스트 1개 추가

