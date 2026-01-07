# AI Gateway (FastAPI) — v0.3 (Ops-ready)

이 디렉터리는 `docs/newarchitecture/gateway`의 **참조 구현**을 실제 서비스 코드로 승격한 것입니다.

## 요구사항 출처
- `docs/newarchitecture/PRD.md`
- `docs/newarchitecture/AGENTS.md` (Non‑negotiables)
- `docs/newarchitecture/gateway/README.md`
- `docs/newarchitecture/docs/FINANCIAL_SUBMISSION_NOTES.md`

## Run (dev)
```bash
cd apps/gateway
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export JWT_DEV_MODE=true
export UPSTREAM_AUTH_MODE=none
uvicorn app.main:app --host 0.0.0.0 --port 8081
```

## OpenAPI pin
- `scripts/generate_openapi.py` → `openapi/openapi.json` 생성
- `scripts/verify_openapi.py` → 런타임 스키마와 pinned 스키마가 동일한지 검증

