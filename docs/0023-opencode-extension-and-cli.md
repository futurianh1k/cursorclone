# 0023 - OpenCode: VS Code 확장(VSIX) + CLI 구성 가이드(온프레미스)

질문: “Copilot처럼 opencode를 쓰려면 별도의 GUI가 필요한가?”

## 결론(요약)

- **별도의 독립 GUI 앱이 ‘필수’는 아닙니다.**
- 일반적으로는 **VS Code 확장(UI) + opencode.ai CLI(로컬 백엔드)** 조합으로 IDE 안에서 Copilot처럼 사용합니다.
- 즉, 사용자가 체감하는 UI는 **VS Code(또는 code-server) 안의 확장 UI**입니다.

## 왜 CLI가 필요한가?

OpenCode VS Code 확장은 보통 다음 중 하나를 수행합니다.

- 확장 내부 UI(명령/패널/키바인딩) 제공
- 실제 “에이전트/분석/실행”은 로컬 CLI(또는 로컬 데몬/서버)를 호출해 수행

그래서 **확장만 설치하면 UI는 보이지만 기능이 동작하지 않을 수 있고**, CLI가 필요합니다.

## 온프레미스 권장 배포 패턴(이 레포 기준)

이 레포는 외부 다운로드 없이도(또는 최소화하여) IDE에 opencode를 탑재할 수 있도록 아래를 지원합니다.

- **VSIX(확장)**: `ide-extensions/`에 넣어두면 IDE 시작 시 자동 설치
- **CLI(실행 파일)**: `opencode-cli/`에 넣어두면 IDE 시작 시 PATH에 추가

상세 절차는:
- `docs/0022-ide-offline-vsix-extensions.md` (VSIX 오프라인 탑재)
- `opencode-cli/README.md` (CLI 오프라인 탑재)

## 참고(사용자 제공 정보)

- OpenCode VS Code 확장은 Open VSX Registry에서 VSIX 다운로드 가능
- CLI는 opencode.ai 공식 경로로 설치 필요

> 주의: 금융권/VDE 환경에서는 Open VSX 접근이 막혀 있을 수 있으니,
> 인터넷 가능한 환경에서 VSIX를 내려받아 내부로 반입하는 절차(승인/검증)를 권장합니다.

