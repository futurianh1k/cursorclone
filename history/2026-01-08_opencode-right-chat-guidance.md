# 변경 내역: OpenCode 사용 가이드(오른쪽 CHAT 오류 구분) 추가 (2026-01-08)

## 요청자(사용자) 요구사항 요약

- 오른쪽 창에서 opencode AI Agent를 사용하려면 어떻게 해야 하는지
- opencode에서 사용할 LLM/RAG는 사내망 모델을 사용할 예정

## Assistant(제가) 응답 내용(무엇을 할지)

- 오른쪽 CHAT 패널이 OpenCode가 아니라 Copilot Chat UI일 수 있음을 명확히 하고,
  OpenCode의 정상 사용 경로(터미널 기반)를 문서화한다.
- 사내망 LLM/RAG 사용을 위해 opencode CLI의 설정 키가 확정되면, 워크스페이스 생성 시 자동 주입하도록 확장 가능함을 안내한다.

## 실제로 수행한 변경 내용(파일/설계 요약)

- `docs/0029-opencode-usage-in-code-server.md` 추가
  - Copilot Chat 오류 원인/대체 경로(Continue 채팅)
  - OpenCode 실행 방법(단축키/명령 팔레트)
  - opencode CLI 필요 조건/오프라인 탑재 경로
  - 사내망 LLM/RAG 연결 시 필요한 추가 정보(설정 키) 정리
- `docs/0020-demo-scenario.md` 업데이트
  - 데모 시 오른쪽 CHAT 패널(Copilot Chat) 사용을 피하고 Continue UI를 사용할 것 주의 추가
- `docs/0029-session-notes.md` 추가(요약+해시)

## 테스트 및 검증 방법

- IDE에서 `Ctrl+Esc`로 “Open opencode” 실행되는지 확인
- `opencode` CLI가 PATH에 있고 실행 가능한지 확인

## 향후 작업 제안 또는 주의사항

- opencode CLI의 LLM/RAG 설정 환경변수/설정 파일 스키마가 확인되면,
  Gateway 엔드포인트(`/v1/chat/*`, `/v1/rag/*`)로 자동 구성 주입을 추가할 수 있습니다.

