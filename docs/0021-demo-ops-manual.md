# 0021 - 시연(데모) 운영 매뉴얼(진행자/운영자용) — Cursor On-Prem PoC

대상: 데모 진행자(엔지니어), 운영자  
목표: “데모가 깨지지 않게” **사전 점검/기동/문제 대응/복구**를 빠르게 수행

> 보안 원칙(중요)
> - 토큰/JWT/비밀번호/내부 토큰을 문서/로그/화면공유에 남기지 마세요.
> - 데모는 반드시 **데모 전용 계정/조직**으로 수행하세요.

---

## 1) 데모 전 5분 점검(필수)

### 1-1) 컨테이너 상태

```bash
cd /home/ubuntu/projects/cursor-onprem-poc
docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
```

### 1-2) 헬스 체크

```bash
curl -fsS http://localhost:3000/api/health
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8081/healthz
```

### 1-3) (선택) Tabby/vLLM/Qdrant 확인

```bash
# Tabby (직접)
curl -fsS http://localhost:8082/v1/health || true

# Qdrant (직접)
curl -fsS http://localhost:6333/collections | python -m json.tool || true
```

---

## 2) 데모 환경변수(권장)

> 실제 배포에서는 `.env`/Secret Manager/Vault를 사용하세요.

- Web: `NEXT_PUBLIC_GATEWAY_URL`, `NEXT_PUBLIC_API_URL`
- Gateway: `JWT_JWKS_URL`(또는 jwks file), DLP 규칙 경로, Upstreams
- API: `GATEWAY_INTERNAL_TOKEN`(Gateway→API 내부 토큰), 오프라인 임베딩 설정 등

---

## 3) 데모 계정/워크스페이스 준비

권장:
- **IDE warmup용 워크스페이스 1개**(미리 running 상태)
- **라이브 생성용 워크스페이스 1개**(대시보드에서 생성 시연)

운영자가 복붙으로 검증하려면 `docs/0015-whitelabel-e2e-runbook.md`를 사용하세요.

---

## 4) 자주 깨지는 지점 & 즉시 대응

### 4-1) Web에서 IDE 시작 시 “Failed to fetch”가 뜸

원인 후보:
- Web이 API를 잘못된 주소로 호출(컨테이너 내부 주소/외부 주소 혼동)
- 브라우저에서 `localhost:8000` 접근이 불가한 환경(리버스 프록시/방화벽)

즉시 대응:
- 브라우저에서 `http://<host>:8000/health`가 열리는지 확인
- `docker-compose.yml`의 Web 환경변수 `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GATEWAY_URL` 재확인

### 4-2) IDE는 열리는데 Tabby가 “Connect to Server Failed”

원인 후보:
- Gateway 라우팅(`/v1/completions`, `/v1/health`)이 Tabby upstream을 못 보고 있음
- IDE 설정 주입 실패(탭비 endpoint/token)

즉시 대응(운영자):
- Gateway 헬스: `curl -fsS http://localhost:8081/healthz`
- Tabby 헬스(직접): `curl -fsS http://localhost:8082/v1/health`
- 가능하면 IDE 컨테이너 내부 설정 파일(마운트) 확인:
  - `/home/coder/.local/share/code-server/User/settings.json`
  - `/home/coder/.config/tabby/settings.json`
  - `/home/coder/.continue/config.json`

### 4-3) Continue 채팅이 401/403/응답 없음

원인 후보:
- 워크스페이스 스코프 토큰 만료/주입 실패
- Gateway JWT/JWKS 설정 불일치
- vLLM upstream 장애/워밍업

즉시 대응:
- IDE 재시작(워크스페이스 재오픈)으로 토큰 재주입 유도
- 짧은 프롬프트로 재시도(“ping”, “한 문장 요약”)

### 4-4) RAG 검색 결과가 비어있음

원인 후보:
- 인덱싱을 수행하지 않았거나 워크스페이스 코드가 적음
- 오프라인 임베딩 모델 미배치(Strict 모드)
- Qdrant 컬렉션 상태 문제

즉시 대응:
- `docs/0015-whitelabel-e2e-runbook.md`의 `/v1/rag/index` → `/v1/rag/stats` 순서로 확인

---

## 5) 데모 복구/리셋(권장 순서)

> 위험: 워크스페이스 삭제는 데이터 손실이 있습니다. 데모 계정/데모 워크스페이스만 대상으로 제한하세요.

- 1) Web 새로고침 / 재로그인
- 2) IDE 컨테이너 재시작(해당 워크스페이스만)
- 3) Tabby/vLLM/Qdrant 컨테이너 재시작(필요 시)
- 4) 최후 수단: 데모 워크스페이스 재생성

---

## 참고

- 데모 진행 스크립트: `docs/0020-demo-scenario.md`
- 사용자 매뉴얼: `docs/0018-solution-user-manual.md`
- 운영 복붙 runbook: `docs/0015-whitelabel-e2e-runbook.md`

