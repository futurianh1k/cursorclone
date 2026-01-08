# 2026-01-08 — Embedding Offline v1 (local_files_only)

## 요청자 요구사항 요약
- (C) 로컬/서버 모델 서빙 중 임베딩은 “외부 다운로드 없이” 동작해야 함
  - 금융권 VDE 제약: 인터넷 의존성 제거
  - 모델/캐시는 사전 배포 및 볼륨으로 유지

## Assistant 응답(무엇을 할지)
- API의 `EmbeddingService`가 로컬 경로 기반으로 모델을 로딩하고,
  오프라인 모드(local_files_only)에서 네트워크 호출을 차단하도록 구성한다.
- 오프라인 모드에서는 mock 폴백을 금지(Strict)해 운영에서 조용히 품질 저하가 발생하지 않게 한다.
- 테스트로 오프라인 동작을 고정한다.

## 실제 수행 변경(요약)
- `EmbeddingService`
  - `EMBEDDING_MODEL_PATH`, `EMBEDDING_CACHE_DIR`, `EMBEDDING_LOCAL_FILES_ONLY`, `EMBEDDING_STRICT` 지원
  - local_files_only=true이면 `TRANSFORMERS_OFFLINE=1`, `HF_HUB_OFFLINE=1` 설정
  - strict/offline 모드에서 모델 로딩 실패 시 명확히 실패(폴백 금지)
- `docker-compose.yml`
  - 모델 디렉토리(`/models`) read-only 마운트
  - HuggingFace 캐시(`vllm_cache`)를 API에도 마운트해 재시작에도 유지
  - 관련 env 추가
- 테스트
  - `test_embedding_offline.py` 추가

## 변경 파일 목록
- `apps/api/src/services/embedding_service.py`
- `apps/api/tests/test_embedding_offline.py`
- `docker-compose.yml`
- `docs/0013-embedding-offline-v1.md`

## 테스트 및 검증 방법
- `cd apps/api && pytest -q`

## 향후 작업 제안/주의사항
- 운영에서는 `EMBEDDING_LOCAL_FILES_ONLY=true` + `EMBEDDING_STRICT=true` 권장
- 모델 배포 방식(사전 다운로드/내부 레지스트리/아티팩트 저장소)을 표준화해야 함

