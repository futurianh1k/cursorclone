# 2025-12-31 - Context Builder 설계 문서 작성

## 사용자 요구사항

- PDF 문서(Cursor 온프레미스 PoC 전체 대화 정리)에서 언급된 Context Builder 설계 문서가 누락되어 있음
- Context Builder는 API와 LLM 사이의 핵심 중간 계층으로, 설계 문서 신규 작성 요청

## 구현 답변

Context Builder 설계 문서를 `docs/context-builder.md`에 작성했습니다. 문서에 포함된 내용:

1. **개요 및 설계 원칙**: API→LLM 중간 계층으로서의 역할 정의
2. **아키텍처**: Context Collector, Security Filter, Template Registry, Prompt Assembler 컴포넌트 설계
3. **컨텍스트 소스**: PoC 범위(Selection, Current File, Instruction)와 확장 예정 항목
4. **인터페이스 설계**: Pydantic 모델 기반 Request/Response 정의
5. **프롬프트 템플릿 시스템**: 기존 `packages/prompt-templates/` 활용 방안
6. **보안 필터**: 경로 검증, Workspace 격리, 확장자 Allowlist
7. **감사 로그**: 원문 저장 금지, hash + 메타데이터만 저장 정책
8. **구현 계획**: 단계별 구현 일정 (5.5일 예상)
9. **테스트 계획**: 단위/통합 테스트 시나리오
10. **향후 확장**: Token Optimizer, Repo Index 연동, Streaming 지원

## 수정 내역 요약

### 추가된 파일
- `docs/context-builder.md`: Context Builder 설계 문서 (신규)
- `history/2025-12-31_context-builder-design.md`: 변경 이력 문서 (본 문서)

### 주요 설계 결정
- **API는 LLM을 직접 호출하지 않음**: AGENTS.md 규칙 준수
- **보안 우선**: 경로 탈출 방지, 심볼릭 링크 검증, 확장자 Allowlist
- **로그 정책**: 프롬프트/응답 원문 저장 금지, hash만 저장

### 태스크 의존성 정의
```
Task C (Diff 유틸) ─────┐
                        ├──▶ Context Builder ──▶ Task D (LLM Router)
Task B (API 명세) ──────┘
```

## 테스트

- 설계 문서이므로 별도 테스트 코드 없음
- 구현 시 `tests/test_context_builder.py`에 테스트 작성 예정
- 테스트 시나리오는 문서 내 섹션 9에 정의됨

## 향후 작업

1. Context Builder 구현 (Task B, C 완료 후)
2. 프롬프트 템플릿 확장 (`packages/prompt-templates/system/`, `user/`)
3. Task D (vLLM Router)와 연동

## 참고

- **원본 요구사항**: `docs/Cursor_온프레미스_PoC_전체_대화_정리.pdf`
- **관련 문서**: `docs/architecture.md`, `AGENTS.md`
