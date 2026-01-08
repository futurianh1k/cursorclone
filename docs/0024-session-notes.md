# 0024 - 대화/작업 기록(요약 + 해시)

> 보안 원칙: 프롬프트/응답 원문을 저장하지 않습니다. 필요 시 **해시 + 메타데이터**만 기록합니다.

## 사용자 요청(요약)

- OpenCode는 VSIX(Open VSX) + CLI(opencode.ai)가 필요하다고 했는데, Copilot처럼 쓰려면 별도 GUI가 필요한지 질문
- code-server 워크스페이스/IDE 시작 시 opencode가 기본 탑재되도록(확장 + CLI) 구성

## 사용자 요청 원문 해시

- sha256: `cc3025ca84ed3b75a1df3141e7ff110e70e7a5ca3e81c7a60f07257c2c2ef111`

## Assistant가 수행한 작업(요약)

- IDE 컨테이너에 opencode CLI 오프라인 마운트(`/opt/opencode-cli`) + PATH 주입 추가
- docker-compose에 `HOST_OPENCODE_CLI_PATH` 추가
- `opencode-cli/` 폴더 가이드, 문서(`docs/0023`) 추가
- 관련 테스트 추가

