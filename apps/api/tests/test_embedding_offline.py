"""
EmbeddingService 오프라인(local_files_only) 동작 테스트
"""

import types
import pytest


@pytest.mark.asyncio
async def test_offline_mode_sets_env_and_passes_local_files_only(monkeypatch, tmp_path):
    # sentence_transformers 모듈을 가짜로 주입해서 외부 다운로드 없이 init 경로만 검증
    calls = {}

    class FakeST:
        def __init__(self, model_source, **kwargs):
            calls["model_source"] = model_source
            calls["kwargs"] = kwargs

        def get_sentence_embedding_dimension(self):
            return 8

        def encode(self, texts, convert_to_numpy=True):
            # not used in this test
            return [[0.0] * 8 for _ in texts]

    fake_mod = types.SimpleNamespace(SentenceTransformer=FakeST)
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", fake_mod)

    monkeypatch.setenv("USE_LOCAL_EMBEDDING", "true")
    monkeypatch.setenv("EMBEDDING_LOCAL_FILES_ONLY", "true")
    monkeypatch.setenv("EMBEDDING_STRICT", "true")
    monkeypatch.setenv("EMBEDDING_MODEL_PATH", str(tmp_path))  # 존재하는 로컬 경로
    monkeypatch.setenv("EMBEDDING_CACHE_DIR", str(tmp_path / "hf_cache"))

    from src.services.embedding_service import EmbeddingService

    svc = EmbeddingService()
    await svc.initialize()

    assert __import__("os").environ.get("TRANSFORMERS_OFFLINE") == "1"
    assert __import__("os").environ.get("HF_HUB_OFFLINE") == "1"
    assert calls["model_source"] == str(tmp_path)
    # sentence-transformers 버전에 따라 local_files_only가 지원되지 않을 수 있어, 지원되는 경우에만 체크
    assert calls["kwargs"].get("cache_folder") == str(tmp_path / "hf_cache")
    assert calls["kwargs"].get("device") == "cpu"
    assert calls["kwargs"].get("local_files_only") is True


@pytest.mark.asyncio
async def test_offline_strict_raises_when_model_path_missing(monkeypatch, tmp_path):
    # sentence_transformers 모듈이 테스트 환경에 없을 수 있으므로 가짜로 주입
    class FakeST:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Should not be instantiated when model path is missing")

    fake_mod = types.SimpleNamespace(SentenceTransformer=FakeST)
    monkeypatch.setitem(__import__("sys").modules, "sentence_transformers", fake_mod)

    monkeypatch.setenv("USE_LOCAL_EMBEDDING", "true")
    monkeypatch.setenv("EMBEDDING_LOCAL_FILES_ONLY", "true")
    monkeypatch.setenv("EMBEDDING_STRICT", "true")
    monkeypatch.setenv("EMBEDDING_MODEL_PATH", str(tmp_path / "missing"))

    from src.services.embedding_service import EmbeddingService

    svc = EmbeddingService()
    with pytest.raises(RuntimeError, match="EMBEDDING_MODEL_PATH not found"):
        await svc.initialize()

