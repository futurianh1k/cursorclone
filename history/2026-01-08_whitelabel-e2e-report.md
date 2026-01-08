# 2026-01-08 — 화이트라벨 E2E 리포트(JSON/MD) 옵션 추가

## 요청자 요구사항 요약
- E2E 검증(화이트라벨 SaaS) 실행 결과를 **자동 리포트(JSON/Markdown)** 로 남기고 싶다.
- 단, **민감정보(비밀번호/토큰)는 저장 금지**.

## Assistant 응답(무엇을 할지)
- `scripts/e2e/whitelabel_e2e.sh` 실행 결과를 파일로 남기는 옵션을 추가한다.
- 리포트에는 성공/실패, 상태코드, 생성된 리소스 ID 등 메타데이터만 포함하고
  비밀번호/토큰은 저장하지 않는다.

## 실제 수행 변경(요약)
- `scripts/e2e/e2e_report.py` 추가
  - `reports/e2e/*.json`, `reports/e2e/*.md` 생성
  - 이메일은 마스킹 처리
  - 비밀번호/토큰은 저장하지 않음
- `.gitignore`에 `reports/` 추가(리포트 산출물이 커밋되지 않도록)

## 사용 방법
- 기본(리포트 생성):
  - `scripts/e2e/whitelabel_e2e.sh`
- 비활성화:
  - `E2E_REPORT=0 scripts/e2e/whitelabel_e2e.sh`

