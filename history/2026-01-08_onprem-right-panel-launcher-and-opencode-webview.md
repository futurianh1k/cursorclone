# 변경 내역: 온프레미스 오른쪽 패널 런처 UI + OpenCode Chat(Webview) (2026-01-08)

## 요청자(사용자) 요구사항 요약

- Copilot Chat 없이(on-prem 인터넷 차단 환경) 오른쪽 패널에서 사용할 런처 UI(버튼/상태 표시) 확장
- OpenCode 용 채팅 UI(Webview) 개발
- Continue는 ide-extensions에 VSIX로 제공(운영자 마운트)됨

## Assistant(제가) 응답 내용(무엇을 할지)

- 내장 VSIX에 Webview 기반 런처(Continue/OpenCode/Chat 버튼 + 상태)를 추가한다.
- OpenCode “전용” 채팅 UI는 opencode CLI 웹서버가 아닌, 현재 온프레미스 아키텍처에 맞게 **AI Gateway(/v1/chat, /v1/rag/context)** 로 호출하는 Webview로 구현한다.
- 토큰/민감정보는 저장하지 않고, 기존 설정(예: `tabby.api.authToken` 또는 `~/.continue/config.json`)에서 읽기만 한다.

## 실제로 수행한 변경 내용(파일/설계 요약)

- 내장 VSIX(`cursor-onprem.onprem-chat-panel`) 기능 확장
  - Webview View 추가: 런처 + OpenCode Chat
  - 설정 키 추가: Gateway apiBase/tokenSource/chat model 등
- 문서 추가/업데이트
  - `docs/0030-onprem-right-panel-chat.md` 업데이트
  - `docs/0031-opencode-chat-webview.md` 추가
- 테스트 보강
  - `apps/api/tests/test_onprem_chat_panel_extension_artifacts.py`에 뷰/커맨드/아이콘 존재 검사 추가

## 테스트 및 검증 방법

- `pytest -q apps/api/tests/test_onprem_chat_panel_extension_artifacts.py`
- IDE 접속 후 Activity Bar의 **On-Prem Agents** 아이콘 확인
- 런처 버튼:
  - Continue/OpenCode/Chat이 정상 실행되는지 확인
- Chat(Webview):
  - `RAG context 포함` 체크 시 `/v1/rag/context` 호출이 성공하는지 확인
  - 응답이 `/v1/chat/completions`로부터 정상 수신되는지 확인

## 향후 작업 제안 또는 주의사항

- opencode CLI가 컨테이너에 제공되면(현재는 README만 존재), Webview가 CLI 기반(`opencode --port`) UI를 iframe/bridge로 붙이는 옵션을 추가할 수 있음(추가 보안/CSP 검토 필요).
- Webview에서 토큰/대화 로그를 파일로 저장하지 않도록 유지(정책 준수).

