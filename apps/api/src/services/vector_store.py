"""
벡터 저장소 서비스
Qdrant를 사용한 코드 임베딩 저장 및 검색

참조:
- Qdrant Python Client: https://github.com/qdrant/qdrant-client
- Qdrant Documentation: https://qdrant.tech/documentation/
"""

import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import asyncio

logger = logging.getLogger(__name__)


# ============================================================
# 설정
# ============================================================

QDRANT_HOST = os.getenv("QDRANT_HOST", "cursor-poc-qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_GRPC_PORT = int(os.getenv("QDRANT_GRPC_PORT", "6334"))

# 컬렉션 설정
CODE_COLLECTION_NAME = "code_embeddings"
DEFAULT_VECTOR_SIZE = 768


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class SearchResult:
    """검색 결과"""
    chunk_id: str
    score: float
    content: str
    file_path: str
    start_line: int
    end_line: int
    language: str
    workspace_id: str
    metadata: Dict[str, Any] = None


# ============================================================
# 벡터 저장소 서비스
# ============================================================

class VectorStoreService:
    """Qdrant 기반 벡터 저장소"""
    
    def __init__(self):
        self._client = None
        self._initialized = False
    
    async def initialize(self, vector_size: int = DEFAULT_VECTOR_SIZE):
        """Qdrant 클라이언트 초기화 및 컬렉션 생성"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
            
            # 비동기 클라이언트 생성
            self._client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
                timeout=30,
            )
            
            # 컬렉션 존재 확인
            collections = self._client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if CODE_COLLECTION_NAME not in collection_names:
                # 컬렉션 생성
                self._client.create_collection(
                    collection_name=CODE_COLLECTION_NAME,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE,
                    ),
                    # 최적화 설정
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=20000,
                    ),
                )
                logger.info(f"Created Qdrant collection: {CODE_COLLECTION_NAME}")
            
            # 인덱스 생성 (검색 최적화)
            self._client.create_payload_index(
                collection_name=CODE_COLLECTION_NAME,
                field_name="workspace_id",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self._client.create_payload_index(
                collection_name=CODE_COLLECTION_NAME,
                field_name="file_path",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            self._client.create_payload_index(
                collection_name=CODE_COLLECTION_NAME,
                field_name="language",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            
            self._initialized = True
            logger.info(f"Vector store initialized: {QDRANT_HOST}:{QDRANT_PORT}")
            
        except ImportError:
            logger.error("qdrant-client not installed")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    async def upsert_embeddings(
        self,
        chunk_ids: List[str],
        embeddings: List[List[float]],
        payloads: List[Dict[str, Any]]
    ) -> bool:
        """임베딩 업서트"""
        if not self._initialized:
            await self.initialize()
        
        try:
            from qdrant_client.http import models
            import uuid
            
            points = []
            for chunk_id, embedding, payload in zip(chunk_ids, embeddings, payloads):
                # chunk_id를 UUID로 변환 (Qdrant는 UUID 또는 정수만 허용)
                # hex string을 UUID 형식으로 변환
                uuid_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))
                
                points.append(models.PointStruct(
                    id=uuid_id,
                    vector=embedding,
                    payload={**payload, "original_chunk_id": chunk_id},
                ))
            
            # 배치 업서트
            self._client.upsert(
                collection_name=CODE_COLLECTION_NAME,
                points=points,
            )
            
            logger.info(f"Upserted {len(points)} embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert embeddings: {e}")
            return False
    
    async def search(
        self,
        query_embedding: List[float],
        workspace_id: str,
        limit: int = 10,
        score_threshold: float = 0.5,
        file_filter: Optional[str] = None,
        language_filter: Optional[str] = None,
    ) -> List[SearchResult]:
        """유사도 검색"""
        if not self._initialized:
            await self.initialize()
        
        try:
            from qdrant_client.http import models
            
            # 필터 조건 구성
            must_conditions = [
                models.FieldCondition(
                    key="workspace_id",
                    match=models.MatchValue(value=workspace_id),
                )
            ]
            
            if file_filter:
                must_conditions.append(
                    models.FieldCondition(
                        key="file_path",
                        match=models.MatchText(text=file_filter),
                    )
                )
            
            if language_filter:
                must_conditions.append(
                    models.FieldCondition(
                        key="language",
                        match=models.MatchValue(value=language_filter),
                    )
                )
            
            # 검색 실행 (qdrant-client 1.7+에서는 query_points 사용)
            results = self._client.query_points(
                collection_name=CODE_COLLECTION_NAME,
                query=query_embedding,
                query_filter=models.Filter(must=must_conditions),
                limit=limit,
                score_threshold=score_threshold,
            ).points
            
            # 결과 변환
            search_results = []
            for result in results:
                payload = result.payload or {}
                search_results.append(SearchResult(
                    chunk_id=str(result.id),
                    score=result.score,
                    content=payload.get("content", ""),
                    file_path=payload.get("file_path", ""),
                    start_line=payload.get("start_line", 0),
                    end_line=payload.get("end_line", 0),
                    language=payload.get("language", ""),
                    workspace_id=payload.get("workspace_id", ""),
                    metadata=payload.get("metadata", {}),
                ))
            
            logger.info(f"Search returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def delete_by_workspace(self, workspace_id: str) -> bool:
        """워크스페이스의 모든 임베딩 삭제"""
        if not self._initialized:
            await self.initialize()
        
        try:
            from qdrant_client.http import models
            
            self._client.delete(
                collection_name=CODE_COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="workspace_id",
                                match=models.MatchValue(value=workspace_id),
                            )
                        ]
                    )
                ),
            )
            
            logger.info(f"Deleted embeddings for workspace: {workspace_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete embeddings: {e}")
            return False
    
    async def delete_by_file(self, workspace_id: str, file_path: str) -> bool:
        """특정 파일의 임베딩 삭제"""
        if not self._initialized:
            await self.initialize()
        
        try:
            from qdrant_client.http import models
            
            self._client.delete(
                collection_name=CODE_COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="workspace_id",
                                match=models.MatchValue(value=workspace_id),
                            ),
                            models.FieldCondition(
                                key="file_path",
                                match=models.MatchValue(value=file_path),
                            ),
                        ]
                    )
                ),
            )
            
            logger.info(f"Deleted embeddings for file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file embeddings: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """컬렉션 통계"""
        if not self._initialized:
            await self.initialize()
        
        try:
            info = self._client.get_collection(collection_name=CODE_COLLECTION_NAME)
            # qdrant-client 버전에 따라 속성 이름이 다를 수 있음
            vectors_count = getattr(info, 'vectors_count', None) or getattr(info, 'indexed_vectors_count', 0)
            points_count = getattr(info, 'points_count', 0)
            status_val = info.status.value if hasattr(info.status, 'value') else str(info.status)
            
            return {
                "vectors_count": vectors_count,
                "points_count": points_count,
                "status": status_val,
                "config": {
                    "vector_size": info.config.params.vectors.size,
                    "distance": info.config.params.vectors.distance.value if hasattr(info.config.params.vectors.distance, 'value') else str(info.config.params.vectors.distance),
                }
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    async def close(self):
        """클라이언트 종료"""
        if self._client:
            self._client.close()
            self._client = None
            self._initialized = False


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_vector_store: Optional[VectorStoreService] = None


async def get_vector_store() -> VectorStoreService:
    """벡터 저장소 싱글톤 가져오기"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
        await _vector_store.initialize()
    return _vector_store
