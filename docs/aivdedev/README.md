# AI VDE Development Platform

본 프로젝트는 금융권 VDE 환경에서 **브라우저 기반 VS Code + Cursor/Codex 급 AI 코딩 서비스**를
구축하기 위한 내부 개발 플랫폼이다.

## 핵심 제약
- 로컬 PC IDE 설치 불가
- 외부 인터넷 차단
- 금융권 보안/감사/망분리 준수

## 핵심 구성
- Web IDE: code-server
- AI Coding: Tabby (Autocomplete), Continue (Chat/Edit/Agent)
- AI Gateway: FastAPI 기반 정책/감사/라우팅
- Deployment: Kubernetes / VM