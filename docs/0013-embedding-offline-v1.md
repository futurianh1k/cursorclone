# 0013 - Embedding Offline v1 (local_files_only)

## 목표
금융권/VDE 환경에서 **외부 네트워크 없이** 임베딩이 동작하도록,
API의 `EmbeddingService`가 HuggingFace 모델을 **로컬 경로/캐시만 사용**하여 로딩할 수 있게 한다.

## 구현 요약
### 환경 변수
- `EMBEDDING_MODEL_PATH`
  - 로컬 모델 경로(디렉토리). 예: `/models/embedding`
- `EMBEDDING_CACHE_DIR`
  - HuggingFace 캐시 경로. 예: `/root/.cache/huggingface`
- `EMBEDDING_LOCAL_FILES_ONLY=true`
  - 오프라인 강제(네트워크 호출 금지). 내부적으로 `TRANSFORMERS_OFFLINE=1`, `HF_HUB_OFFLINE=1`을 설정
- `EMBEDDING_STRICT=true`
  - 임베딩 백엔드가 준비되지 않으면 **mock으로 폴백하지 않고 실패**

### 동작
- `EMBEDDING_LOCAL_FILES_ONLY=true` 이면:
  - 모델 로딩 실패 시 에러로 종료(조용히 mock으로 떨어지지 않음)
  - 모델은 `EMBEDDING_MODEL_PATH` 또는 캐시에 미리 준비되어 있어야 함

## docker-compose 반영
- `api` 서비스에 다음을 추가:
  - `./models:/models:ro` (모델 디렉토리)
  - `vllm_cache:/root/.cache/huggingface` (캐시 공유)
  - 관련 env(`EMBEDDING_MODEL_PATH`, `EMBEDDING_CACHE_DIR`, `EMBEDDING_LOCAL_FILES_ONLY`, `EMBEDDING_STRICT`)

## 테스트
- `apps/api/tests/test_embedding_offline.py`
  - 오프라인 모드에서 offline env 강제 및 local_files_only 전달 확인
  - 모델 경로가 없으면 명확한 RuntimeError 발생 확인

