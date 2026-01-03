# 금융권 VDE 브라우저 기반 Web IDE + AI 코딩 환경 구축 가이드

> **버전**: 2.0  
> **최종 수정**: 2026-01-03  
> **대상 환경**: 금융권 VDE (Virtual Desktop Environment), 폐쇄망

## 📋 개요

이 프로젝트는 금융권 VDE 환경에서 로컬 PC에 VS Code 설치가 불가능한 상황을 전제로, **브라우저만으로 Cursor/Copilot 수준의 AI 코딩 경험**을 제공하는 인프라를 구축하는 가이드입니다.

### 핵심 목표 3가지

1. **브라우저만으로 개발** - code-server 기반 Web IDE
2. **AI 코딩 어시스턴트** - 인라인 자동완성 + 채팅/에이전트
3. **금융권 수준 통제** - 격리, 감사, 공급망 관리, 데이터 비유출

## 📁 프로젝트 구조

```
vde-web-ide-project/
├── README.md                    # 이 파일
├── docs/
│   ├── 01-ARCHITECTURE.md       # 아키텍처 설계서
│   ├── 02-SECURITY-CONTROLS.md  # 보안 통제 명세서
│   ├── 03-OPERATIONS-GUIDE.md   # 운영 가이드
│   ├── 04-ROADMAP.md            # 구축 로드맵
│   └── 05-PRD.md                # Product Requirements Document
├── scaffold/
│   ├── docker/                  # Docker 구성
│   ├── k8s/                     # Kubernetes 매니페스트
│   ├── nginx/                   # Nginx + OIDC 설정
│   ├── scripts/                 # 자동화 스크립트
│   └── configs/                 # 서비스 설정 파일
└── templates/
    └── CHECKLIST.md             # PoC/Pilot 체크리스트
```

## 🚀 Quick Start

### PoC 환경 빠른 시작 (Docker Compose)

```bash
cd scaffold/docker
docker-compose -f docker-compose.poc.yaml up -d
```

### Production 배포 (Kubernetes)

```bash
cd scaffold/k8s
kubectl apply -k overlays/production/
```

## 📚 문서 가이드

| 문서 | 용도 | 대상 독자 |
|------|------|-----------|
| [아키텍처 설계서](docs/01-ARCHITECTURE.md) | 전체 시스템 구조, 존 구성, 데이터 흐름 | 아키텍트, 인프라 엔지니어 |
| [보안 통제 명세서](docs/02-SECURITY-CONTROLS.md) | 접근통제, 인증, 감사, 공급망 관리 | 보안팀, 감사팀 |
| [운영 가이드](docs/03-OPERATIONS-GUIDE.md) | 일상 운영, 장애 대응, 업데이트 절차 | 운영팀, DevOps |
| [구축 로드맵](docs/04-ROADMAP.md) | PoC → Pilot → Production 단계별 계획 | PM, 의사결정자 |
| [PRD](docs/05-PRD.md) | 제품 요구사항 정의 | 전체 이해관계자 |

## ⚙️ 기술 스택

| 계층 | 선택 기술 | 대안 |
|------|-----------|------|
| Web IDE | code-server | OpenVSCode Server |
| 인라인 자동완성 | Tabby (self-hosted) | - |
| Chat/Edit/Agent | Continue 확장 | Cody |
| Code Intelligence | 자체 RAG 또는 Sourcegraph | - |
| LLM Serving | vLLM / TensorRT-LLM | TGI |
| LLM Gateway | LiteLLM Proxy | Kong + 커스텀 |
| 컨테이너 오케스트레이션 | Kubernetes | Nomad |
| 인증 | Keycloak (OIDC) | ADFS |

## 🔐 금융권 컴플라이언스

이 가이드는 다음 금융권 규제 요건을 고려하여 설계되었습니다:

- **전자금융감독규정** - 접근통제, 감사추적
- **개인정보보호법** - 데이터 처리, 로깅 정책
- **금융보안원 가이드라인** - 클라우드 및 컨테이너 보안

## 📞 지원

문의사항이나 기여는 이슈를 통해 등록해 주세요.

---

**⚠️ 주의사항**: 이 문서는 가이드라인이며, 실제 구축 시 조직의 보안 정책 및 규제 요건에 맞게 조정이 필요합니다.
