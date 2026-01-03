# Architecture Design

## 1. 전체 구조
VDE Browser → Reverse Proxy(SSO) → IDE(code-server) → AI Gateway → LLM Serving

## 2. 구성 요소
- Reverse Proxy: 인증, TLS 종단
- IDE: 사용자별 컨테이너
- AI Gateway: 정책/감사/라우팅
- LLM Serving: GPU 기반

## 3. 데이터 흐름
사용자 입력 → IDE → Gateway → LLM → IDE