# 0030 - 오른쪽 패널 채팅(UI) 기본값: Continue (오프라인/온프레미스)

## 목표

- code-server의 오른쪽 **CHAT(Copilot Chat)** UI 의존을 제거하고,
- 온프레미스(인터넷 차단)에서도 동작하는 **Continue 채팅 UI**를 오른쪽 패널 기본값으로 제공합니다.

## 구현 요약

- 내장 VSIX(`cursor-onprem.onprem-chat-panel`)를 이미지에 포함합니다.
  - IDE 시작 시 `Continue: Toggle Right Sidebar` + `Continue: Focus Input`을 실행하여
    Continue를 오른쪽 패널(Secondary Side Bar / Auxiliary Bar)에 자동으로 띄웁니다.
- 또한 온프레미스 환경에서 **Continue ↔ OpenCode(터미널)** 중 선택할 수 있도록 명령/설정을 제공합니다.
  - 설정: `cursorOnprem.rightPanel.agent` = `continue` | `opencode` | `off`
  - 명령: `On-Prem: Choose Agent (Continue/OpenCode)`
- 운영자가 제공한 VSIX(`/opt/extra-extensions`)가 있더라도, 내장 VSIX(`/opt/builtin-extensions`)는 overlay에 영향을 받지 않도록 분리했습니다.

## 파일/경로

- 내장 VSIX 소스:
  - `docker/code-server/builtin-vsix/onprem-chat-panel/`
- VSIX 설치 디렉토리(컨테이너 내부):
  - `/opt/builtin-extensions/*.vsix` (이미지 내장)
  - `/opt/extra-extensions/*.vsix` (호스트 마운트, 운영자 제공)
- 설치 로직:
  - `docker/code-server/entrypoint.sh`

## 확인 방법(운영자)

- IDE 접속 직후, 오른쪽 패널에 Continue가 자동으로 열리면 성공
- 단축키:
  - `Alt+Ctrl+M`: Continue 오른쪽 사이드바 토글
  - `Ctrl+M`: Continue 입력 포커스

## 보안/온프레미스 주의사항

- Continue의 LLM endpoint는 사내망 Gateway를 사용하도록 구성해야 합니다.
- Copilot Chat(`GitHub.copilot-chat`)은 사용하지 않는 것을 전제로 합니다.

