# 0031 - OpenCode Chat(Webview) - 온프레미스(인터넷 차단)용

## 목적

- VS Code/code-server 오른쪽 영역에서 사용할 수 있는 **OpenCode 스타일 채팅 UI(Webview)** 제공
- 외부 인터넷 없이 **사내망 AI Gateway**(OpenAI 호환 `/v1/*`)로만 호출

## 구현 개요

- 내장 VSIX `cursor-onprem.onprem-chat-panel`에 Webview View를 추가:
  - `cursorOnprem.launcherView`: 런처(Continue/OpenCode/Chat 버튼 + 상태)
  - `cursorOnprem.opencodeChatView`: OpenCode Chat(Webview)

## 호출 경로

- Chat: `POST {apiBase}/chat/completions`
- RAG Context(선택): `POST {apiBase}/rag/context`

여기서 `apiBase`는 `/v1`로 끝나는 URL을 의미합니다.

## 토큰/스코프 처리(민감정보 저장 금지)

- Webview는 토큰을 저장하지 않습니다(세션 메모리만).
- 토큰은 다음 중 하나에서 **읽기만** 합니다:
  - 기본: `tabby.api.authToken` (권장)
  - 대안: `~/.continue/config.json`의 `models[0].apiKey`
  - 선택: 환경변수 `GATEWAY_TOKEN`
- 워크스페이스 스코프는 토큰 JWT의 `wid` claim을 **로컬에서 decode(검증 없이)** 해서 `workspace_id`로 사용합니다.

> 주의: 토큰 값을 로그/출력에 남기지 않도록 구현되어야 합니다.

## 설정 키

- `cursorOnprem.gateway.apiBase`: Gateway base URL(`/v1` 포함)
- `cursorOnprem.gateway.tokenSource`: `tabby` | `continue` | `env` | `none`
- `cursorOnprem.chat.model`: 모델명(미설정 시 Continue config의 models[0].model 사용)

## 사용 방법

- 명령 팔레트:
  - `On-Prem: Open OpenCode Chat (Webview)`
  - `On-Prem: Open Agents Launcher (Right Panel)`
- 런처에서:
  - `OpenCode Chat (Webview)` 버튼 클릭
  - `RAG context 포함` 체크로 context builder 결과를 system message로 주입

