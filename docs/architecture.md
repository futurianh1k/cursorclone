# Architecture (On-Prem PoC)

- Web IDE(Next.js + Monaco) → API(FastAPI) → CI Layer(내장) → LLM(vLLM)
- 코드 변경은 Diff 기반 Patch로만 반영한다.
- Audit Log는 원문 저장 금지(해시 + 메타만).

## MVP API
- /auth/me (stub)
- /workspaces (CRUD 일부)
- /files (tree, read, write)
- /ai/explain (stub)
- /ai/rewrite (stub → diff 반환)
- /patch/validate
- /patch/apply
- WS: /ws/workspaces/{wsId}
