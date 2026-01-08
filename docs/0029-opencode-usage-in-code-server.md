# 0029 - code-server에서 OpenCode(opencode) 사용하기 (오른쪽 CHAT 오류 해결 포함)

## TL;DR

- 오른쪽 **CHAT 패널은 OpenCode가 아니라 “Copilot Chat(GitHub.copilot-chat)” UI**입니다.
  - code-server(Open VSX) 환경에서는 `GitHub.copilot-chat`을 찾지 못해 오류가 날 수 있습니다.
- OpenCode는 **오른쪽 CHAT 패널이 아니라 “터미널 기반 UI”**로 동작합니다.
  - 단축키/명령으로 **opencode 터미널을 열어** 사용하세요.
- 이 PoC는 오프라인/온프레미스 환경을 위해 **오른쪽 패널에 Continue 채팅 UI를 자동으로 띄우는 내장 VSIX**를 포함합니다.
  - 즉, “오른쪽에서 쓰는 채팅 UI”는 **Copilot Chat이 아니라 Continue**가 기본입니다.

---

## 1) 왜 오른쪽 CHAT에서 에러가 나나?

증상:
- “An error occurred while setting up chat… GitHub.copilot-chat cannot be installed…” 팝업

원인:
- VS Code의 기본 Chat UI가 Copilot Chat 확장(`GitHub.copilot-chat`)을 필요로 하는데,
  code-server(Open VSX) 환경에서는 해당 확장을 사용할 수 없어서 설치 실패가 발생합니다.

해결:
- OpenCode 사용은 아래 “2) OpenCode 실행 방법”대로 진행합니다.
- 오른쪽 Chat UI가 필요하면, 현재 PoC에서는 **Continue 확장(채팅 UI)** 를 사용하세요.

---

## 2) OpenCode 실행 방법(정상 경로)

OpenCode VS Code 확장은 “채팅 패널”이 아니라 **통합 터미널에서 `opencode` CLI를 실행**하는 방식입니다.

### 2-1) 단축키(권장)

- **Open opencode**: `Ctrl + Esc` (Linux/Windows)
- **Open opencode in new tab**: `Ctrl + Shift + Esc`

### 2-2) 명령 팔레트

- `Ctrl+Shift+P` → 아래 명령 실행
  - `Open opencode`
  - `Open opencode in new tab`

### 2-3) 컨텍스트 전달(자동)

확장은 현재 파일/선택 영역을 `@파일#라인` 형태로 opencode에 전달합니다.
예:
- `@src/main.py#L10-42`

추가로 파일 참조를 삽입:
- `Alt + Ctrl + K` (Linux/Windows) → file reference 삽입

---

## 3) 필수 조건: opencode CLI

OpenCode 확장은 내부적으로 다음을 수행합니다:
- 터미널에서 `opencode --port <랜덤포트>` 실행
- `http://localhost:<포트>/app` 응답을 확인한 뒤, 프롬프트를 주입

따라서 IDE 컨테이너 안에서 `opencode` 실행 파일이 PATH에 있어야 정상 동작합니다.

이 레포는 오프라인 환경을 위해 다음을 지원합니다:

- `opencode-cli/`를 IDE 컨테이너의 `/opt/opencode-cli`로 ro 마운트
- `/opt/opencode-cli/opencode`가 있으면 PATH에 자동 추가

가이드: `opencode-cli/README.md`

---

## 4) 고객사 사내망 LLM/RAG 사용

원칙:
- LLM/RAG 호출은 고객사 내부 endpoint(예: vLLM, 내부 RAG)로 가야 하며,
  이 PoC에서는 **AI Gateway 경유** 구성을 권장합니다.

중요:
- OpenCode 확장이 호출하는 “opencode CLI”가 **어떤 설정 키/환경변수로 LLM/RAG endpoint를 지정하는지**가 확정되어야 합니다.
  (도구별로 `OPENAI_BASE_URL`, `OPENAI_API_KEY` 같은 표준을 쓰기도 하고, 별도 config 파일을 쓰기도 합니다.)

다음 중 하나가 확인되면, 우리 쪽에서 “워크스페이스 생성 시 자동 설정 주입”까지 붙일 수 있습니다.
- opencode CLI의 config 파일 위치/스키마
- opencode CLI가 읽는 환경변수 이름(LLM base url, api key, rag url 등)

---

## 5) 참고(현재 설치된 확장)

- `sst-dev.opencode` (터미널 기반)
- `Continue.continue` (채팅 UI)
- `TabbyML.vscode-tabby` (자동완성)

