"""
코드 임베딩 서비스
코드 청크를 벡터로 변환하여 RAG 검색에 활용

참조:
- Sentence Transformers: https://www.sbert.net/
- vLLM Embeddings: https://docs.vllm.ai/en/latest/
"""

import os
import logging
import hashlib
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import asyncio
import httpx

logger = logging.getLogger(__name__)


# ============================================================
# 설정
# ============================================================

# 임베딩 모델 설정
# 로컬 임베딩 모델 (sentence-transformers) 또는 vLLM 임베딩 사용
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-base-en-v1.5")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
EMBEDDING_MODEL_PATH = os.getenv("EMBEDDING_MODEL_PATH", "").strip()  # 로컬 디렉토리/파일 경로 (권장: VDE/오프라인)
EMBEDDING_CACHE_DIR = os.getenv("EMBEDDING_CACHE_DIR", "").strip()    # HuggingFace 캐시 경로
EMBEDDING_LOCAL_FILES_ONLY = os.getenv("EMBEDDING_LOCAL_FILES_ONLY", "false").lower() == "true"
EMBEDDING_STRICT = os.getenv("EMBEDDING_STRICT", "false").lower() == "true"
EMBEDDING_ALLOW_MOCK = os.getenv("EMBEDDING_ALLOW_MOCK", "true").lower() == "true"

# vLLM 임베딩 서버 (선택적)
VLLM_EMBEDDING_URL = os.getenv("VLLM_EMBEDDING_URL", "")

# 로컬 임베딩 사용 여부
USE_LOCAL_EMBEDDING = os.getenv("USE_LOCAL_EMBEDDING", "true").lower() == "true"


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class CodeChunk:
    """코드 청크 데이터"""
    chunk_id: str
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    workspace_id: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EmbeddingResult:
    """임베딩 결과"""
    chunk_id: str
    embedding: List[float]
    model: str
    dimension: int


# ============================================================
# 코드 청커 (Code Chunker)
# ============================================================

class CodeChunker:
    """코드를 의미 있는 청크로 분할"""
    
    # 언어별 확장자 매핑
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".scala": "scala",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".sql": "sql",
        ".sh": "shell",
        ".bash": "shell",
    }
    
    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 100,
        overlap: int = 100
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
    
    def detect_language(self, file_path: str) -> str:
        """파일 확장자로 언어 감지"""
        ext = os.path.splitext(file_path)[1].lower()
        return self.LANGUAGE_EXTENSIONS.get(ext, "unknown")
    
    def chunk_file(
        self,
        content: str,
        file_path: str,
        workspace_id: str
    ) -> List[CodeChunk]:
        """파일을 청크로 분할"""
        language = self.detect_language(file_path)
        lines = content.split("\n")
        chunks = []
        
        current_chunk_lines = []
        current_start_line = 1
        current_size = 0
        
        for i, line in enumerate(lines, start=1):
            line_size = len(line) + 1  # +1 for newline
            
            # 청크 크기 초과 시 새 청크 시작
            if current_size + line_size > self.max_chunk_size and current_chunk_lines:
                chunk_content = "\n".join(current_chunk_lines)
                
                if len(chunk_content) >= self.min_chunk_size:
                    chunk_id = self._generate_chunk_id(
                        workspace_id, file_path, current_start_line
                    )
                    chunks.append(CodeChunk(
                        chunk_id=chunk_id,
                        content=chunk_content,
                        file_path=file_path,
                        start_line=current_start_line,
                        end_line=i - 1,
                        language=language,
                        workspace_id=workspace_id,
                        metadata={
                            "char_count": len(chunk_content),
                            "line_count": len(current_chunk_lines),
                        }
                    ))
                
                # 오버랩 처리
                overlap_lines = int(self.overlap / (current_size / len(current_chunk_lines)))
                current_chunk_lines = current_chunk_lines[-overlap_lines:] if overlap_lines > 0 else []
                current_start_line = max(1, i - len(current_chunk_lines))
                current_size = sum(len(l) + 1 for l in current_chunk_lines)
            
            current_chunk_lines.append(line)
            current_size += line_size
        
        # 마지막 청크 처리
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            if len(chunk_content) >= self.min_chunk_size:
                chunk_id = self._generate_chunk_id(
                    workspace_id, file_path, current_start_line
                )
                chunks.append(CodeChunk(
                    chunk_id=chunk_id,
                    content=chunk_content,
                    file_path=file_path,
                    start_line=current_start_line,
                    end_line=len(lines),
                    language=language,
                    workspace_id=workspace_id,
                    metadata={
                        "char_count": len(chunk_content),
                        "line_count": len(current_chunk_lines),
                    }
                ))
        
        return chunks
    
    def _generate_chunk_id(
        self,
        workspace_id: str,
        file_path: str,
        start_line: int
    ) -> str:
        """청크 ID 생성"""
        content = f"{workspace_id}:{file_path}:{start_line}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


# ============================================================
# 임베딩 서비스
# ============================================================

class EmbeddingService:
    """코드 임베딩 생성 서비스"""
    
    def __init__(self):
        # NOTE: 테스트/런타임에서 환경변수를 바꿀 수 있으므로, 인스턴스 생성 시점에 env를 다시 읽는다.
        self.model_name = os.getenv("EMBEDDING_MODEL", EMBEDDING_MODEL)
        self.dimension = int(os.getenv("EMBEDDING_DIMENSION", str(EMBEDDING_DIMENSION)))
        self.model_path = os.getenv("EMBEDDING_MODEL_PATH", "").strip()
        self.cache_dir = os.getenv("EMBEDDING_CACHE_DIR", "").strip() or None
        self.local_files_only = os.getenv("EMBEDDING_LOCAL_FILES_ONLY", "false").lower() == "true"
        strict_env = os.getenv("EMBEDDING_STRICT", "false").lower() == "true"
        allow_mock_env = os.getenv("EMBEDDING_ALLOW_MOCK", "true").lower() == "true"

        # 오프라인(local_files_only)에서는 실패를 숨기면 안 됨 (조용히 mock으로 떨어지지 않게)
        self.strict = strict_env or self.local_files_only
        self.allow_mock = (allow_mock_env and not self.strict)

        # 백엔드 선택도 인스턴스 단위로 유지
        self.use_local_embedding = os.getenv("USE_LOCAL_EMBEDDING", "true").lower() == "true"
        self.vllm_embedding_url = os.getenv("VLLM_EMBEDDING_URL", VLLM_EMBEDDING_URL).strip()

        self._model = None
        self._http_client = None
    
    async def initialize(self):
        """임베딩 모델 초기화"""
        if self.use_local_embedding:
            await self._init_local_model()
        else:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"Embedding service initialized: model={self.model_name}")
    
    async def _init_local_model(self):
        """로컬 sentence-transformers 모델 초기화"""
        try:
            from sentence_transformers import SentenceTransformer

            # 오프라인 모드: transformers/hf-hub가 네트워크 호출하지 않도록 강제
            if self.local_files_only:
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                os.environ.setdefault("HF_HUB_OFFLINE", "1")

            # 모델 소스 결정 (로컬 경로 우선)
            model_source = self.model_path or self.model_name
            if self.model_path and not os.path.exists(self.model_path):
                raise RuntimeError(f"EMBEDDING_MODEL_PATH not found: {self.model_path}")

            # CPU에서 실행
            try:
                # sentence-transformers 버전에 따라 local_files_only/cache_folder 파라미터 지원 여부가 다를 수 있어 방어적으로 처리
                kwargs = {"device": "cpu"}
                if self.cache_dir:
                    kwargs["cache_folder"] = self.cache_dir
                if self.local_files_only:
                    kwargs["local_files_only"] = True
                self._model = SentenceTransformer(model_source, **kwargs)
            except TypeError:
                # local_files_only 인자가 없는 구버전 대응: env offline로 방어 후 로딩
                if self.cache_dir:
                    self._model = SentenceTransformer(model_source, device="cpu", cache_folder=self.cache_dir)
                else:
                    self._model = SentenceTransformer(model_source, device="cpu")

            self.dimension = self._model.get_sentence_embedding_dimension()
            logger.info(
                f"Local embedding model loaded: source={model_source}, dim={self.dimension}, "
                f"offline={self.local_files_only}, cache_dir={self.cache_dir or ''}"
            )
        except ImportError:
            msg = "sentence-transformers not installed"
            if self.strict:
                raise RuntimeError(msg)
            logger.warning(f"{msg}, using mock embeddings (development only)")
            self._model = None
        except RuntimeError:
            # 명시적으로 발생시킨 구성 오류(예: EMBEDDING_MODEL_PATH not found)는 그대로 전달
            raise
        except Exception as e:
            if self.strict:
                raise RuntimeError(
                    "Failed to load embedding model in strict/offline mode. "
                    "Pre-download the model into EMBEDDING_MODEL_PATH or HuggingFace cache and retry."
                ) from e
            logger.error(f"Failed to load embedding model: {e}")
            self._model = None
    
    async def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩"""
        embeddings = await self.embed_batch([text])
        return embeddings[0] if embeddings else []
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """배치 텍스트 임베딩"""
        if not texts:
            return []
        
        if self.use_local_embedding and self._model:
            return await self._embed_local(texts)
        elif self.vllm_embedding_url:
            return await self._embed_vllm(texts)
        else:
            # Strict 모드에서는 조용히 mock으로 떨어지지 않는다.
            if self.strict:
                raise RuntimeError(
                    "Embedding backend not available in strict mode. "
                    "Enable local embedding with a local model, or configure VLLM_EMBEDDING_URL."
                )
            # Mock 임베딩 (개발용)
            return await self._embed_mock(texts)
    
    async def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """로컬 모델로 임베딩"""
        try:
            # CPU에서 동기 실행 후 결과 반환
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self._model.encode(texts, convert_to_numpy=True).tolist()
            )
            return embeddings
        except Exception as e:
            logger.error(f"Local embedding failed: {e}")
            if self.strict:
                raise
            return await self._embed_mock(texts)
    
    async def _embed_vllm(self, texts: List[str]) -> List[List[float]]:
        """vLLM 서버로 임베딩"""
        try:
            response = await self._http_client.post(
                f"{self.vllm_embedding_url}/embeddings",
                json={
                    "model": self.model_name,
                    "input": texts,
                }
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
        except Exception as e:
            logger.error(f"vLLM embedding failed: {e}")
            if self.strict:
                raise
            return await self._embed_mock(texts)
    
    async def _embed_mock(self, texts: List[str]) -> List[List[float]]:
        """Mock 임베딩 (개발/테스트용)"""
        import random
        logger.warning("Using mock embeddings - for development only!")
        embeddings = []
        for text in texts:
            # 텍스트 기반 시드로 일관된 임베딩 생성
            seed = hash(text) % (2**32)
            random.seed(seed)
            embedding = [random.uniform(-1, 1) for _ in range(self.dimension)]
            # 정규화
            norm = sum(x**2 for x in embedding) ** 0.5
            embedding = [x / norm for x in embedding]
            embeddings.append(embedding)
        return embeddings
    
    async def embed_chunks(self, chunks: List[CodeChunk]) -> List[EmbeddingResult]:
        """코드 청크 배치 임베딩"""
        if not chunks:
            return []
        
        # 청크 내용에 메타데이터 추가하여 임베딩
        texts = []
        for chunk in chunks:
            # 파일 경로와 언어 정보를 포함하여 컨텍스트 제공
            enriched_text = f"File: {chunk.file_path}\nLanguage: {chunk.language}\n\n{chunk.content}"
            texts.append(enriched_text)
        
        embeddings = await self.embed_batch(texts)
        
        results = []
        for chunk, embedding in zip(chunks, embeddings):
            results.append(EmbeddingResult(
                chunk_id=chunk.chunk_id,
                embedding=embedding,
                model=self.model_name,
                dimension=len(embedding)
            ))
        
        return results
    
    async def close(self):
        """리소스 정리"""
        if self._http_client:
            await self._http_client.aclose()


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_embedding_service: Optional[EmbeddingService] = None
_code_chunker: Optional[CodeChunker] = None


async def get_embedding_service() -> EmbeddingService:
    """임베딩 서비스 싱글톤 가져오기"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        await _embedding_service.initialize()
    return _embedding_service


def get_code_chunker() -> CodeChunker:
    """코드 청커 싱글톤 가져오기"""
    global _code_chunker
    if _code_chunker is None:
        _code_chunker = CodeChunker()
    return _code_chunker
