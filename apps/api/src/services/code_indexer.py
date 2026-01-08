"""
코드 인덱서 서비스
워크스페이스의 코드 파일을 인덱싱하여 벡터 DB에 저장

참조:
- 코드 청킹 전략: https://docs.continue.dev/features/codebase-embeddings
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib

from .embedding_service import (
    CodeChunk,
    CodeChunker,
    EmbeddingService,
    get_embedding_service,
    get_code_chunker,
)
from .vector_store import VectorStoreService, get_vector_store

logger = logging.getLogger(__name__)


# ============================================================
# 설정
# ============================================================

# 인덱싱 대상 확장자
INDEXABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".cpp", ".c", ".h", ".hpp",
    ".cs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".md", ".json", ".yaml", ".yml", ".toml",
    ".sql", ".sh", ".bash",
    ".html", ".css", ".scss", ".less",
}

# 무시할 디렉토리
IGNORE_DIRECTORIES = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".next", "dist", "build", "target", ".idea", ".vscode",
    "coverage", ".pytest_cache", ".mypy_cache",
}

# 무시할 파일
IGNORE_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "poetry.lock", "Pipfile.lock",
}

# 최대 파일 크기 (바이트)
MAX_FILE_SIZE = 1024 * 1024  # 1MB

# 배치 크기
EMBEDDING_BATCH_SIZE = 32


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class IndexingProgress:
    """인덱싱 진행 상태"""
    workspace_id: str
    total_files: int = 0
    indexed_files: int = 0
    total_chunks: int = 0
    indexed_chunks: int = 0
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    @property
    def progress_percent(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (self.indexed_files / self.total_files) * 100


@dataclass
class IndexingResult:
    """인덱싱 결과"""
    workspace_id: str
    files_processed: int
    chunks_created: int
    duration_seconds: float
    success: bool
    error: Optional[str] = None


# ============================================================
# 코드 인덱서 서비스
# ============================================================

class CodeIndexerService:
    """워크스페이스 코드 인덱서"""
    
    def __init__(self):
        self._chunker: Optional[CodeChunker] = None
        self._embedding_service: Optional[EmbeddingService] = None
        self._vector_store: Optional[VectorStoreService] = None
        self._progress: Dict[str, IndexingProgress] = {}
    
    async def initialize(self):
        """서비스 초기화"""
        self._chunker = get_code_chunker()
        self._embedding_service = await get_embedding_service()
        self._vector_store = await get_vector_store()
        logger.info("Code indexer initialized")
    
    def _should_index_file(self, file_path: Path) -> bool:
        """파일 인덱싱 여부 확인"""
        # 확장자 확인
        if file_path.suffix.lower() not in INDEXABLE_EXTENSIONS:
            return False
        
        # 파일명 확인
        if file_path.name in IGNORE_FILES:
            return False
        
        # 파일 크기 확인
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                return False
        except OSError:
            return False
        
        return True
    
    def _should_skip_directory(self, dir_path: Path) -> bool:
        """디렉토리 스킵 여부 확인"""
        return dir_path.name in IGNORE_DIRECTORIES
    
    async def scan_workspace(self, workspace_path: str) -> List[Path]:
        """워크스페이스 파일 스캔"""
        root = Path(workspace_path)
        if not root.exists():
            logger.warning(f"Workspace path not found: {workspace_path}")
            return []
        
        files = []
        for path in root.rglob("*"):
            if path.is_file():
                # 무시할 디렉토리 확인
                skip = False
                for parent in path.parents:
                    if self._should_skip_directory(parent):
                        skip = True
                        break
                
                if not skip and self._should_index_file(path):
                    files.append(path)
        
        logger.info(f"Scanned {len(files)} indexable files in {workspace_path}")
        return files
    
    async def index_workspace(
        self,
        workspace_id: str,
        workspace_path: str,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        force_reindex: bool = False
    ) -> IndexingResult:
        """워크스페이스 전체 인덱싱"""
        start_time = datetime.now(timezone.utc)
        
        # 진행 상태 초기화
        progress = IndexingProgress(
            workspace_id=workspace_id,
            status="running",
            started_at=start_time,
        )
        self._progress[workspace_id] = progress
        
        try:
            # 강제 재인덱싱인 경우 기존 데이터 삭제
            if force_reindex:
                await self._vector_store.delete_by_workspace(workspace_id)
                logger.info(f"Deleted existing embeddings for {workspace_id}")
            
            # 파일 스캔
            files = await self.scan_workspace(workspace_path)
            progress.total_files = len(files)
            
            if not files:
                progress.status = "completed"
                progress.completed_at = datetime.now(timezone.utc)
                return IndexingResult(
                    workspace_id=workspace_id,
                    files_processed=0,
                    chunks_created=0,
                    duration_seconds=0,
                    success=True,
                )
            
            # 파일별 청킹 및 인덱싱
            total_chunks = 0
            all_chunks = []
            
            for file_path in files:
                try:
                    # 파일 읽기
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    
                    # 상대 경로 계산
                    relative_path = str(file_path.relative_to(workspace_path))
                    
                    # 청킹
                    chunks = self._chunker.chunk_file(
                        content=content,
                        file_path=relative_path,
                        workspace_id=workspace_id,
                    )
                    
                    all_chunks.extend(chunks)
                    progress.indexed_files += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to process file {file_path}: {e}")
                    continue
            
            progress.total_chunks = len(all_chunks)
            
            # 배치 임베딩 및 저장
            for i in range(0, len(all_chunks), EMBEDDING_BATCH_SIZE):
                batch = all_chunks[i:i + EMBEDDING_BATCH_SIZE]
                
                # 임베딩 생성
                embedding_results = await self._embedding_service.embed_chunks(batch)
                
                # 벡터 저장소에 저장
                chunk_ids = [r.chunk_id for r in embedding_results]
                embeddings = [r.embedding for r in embedding_results]
                payloads = [
                    {
                        "content": chunk.content,
                        "file_path": chunk.file_path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "language": chunk.language,
                        "workspace_id": chunk.workspace_id,
                        "project_id": project_id,
                        "tenant_id": tenant_id,
                        "metadata": chunk.metadata,
                    }
                    for chunk in batch
                ]
                
                await self._vector_store.upsert_embeddings(
                    chunk_ids=chunk_ids,
                    embeddings=embeddings,
                    payloads=payloads,
                )
                
                progress.indexed_chunks += len(batch)
                total_chunks += len(batch)
            
            # 완료
            end_time = datetime.now(timezone.utc)
            progress.status = "completed"
            progress.completed_at = end_time
            
            duration = (end_time - start_time).total_seconds()
            
            logger.info(
                f"Indexing completed: {workspace_id}, "
                f"files={progress.indexed_files}, chunks={total_chunks}, "
                f"duration={duration:.2f}s"
            )
            
            return IndexingResult(
                workspace_id=workspace_id,
                files_processed=progress.indexed_files,
                chunks_created=total_chunks,
                duration_seconds=duration,
                success=True,
            )
            
        except Exception as e:
            logger.error(f"Indexing failed for {workspace_id}: {e}")
            progress.status = "failed"
            progress.error = str(e)
            progress.completed_at = datetime.now(timezone.utc)
            
            return IndexingResult(
                workspace_id=workspace_id,
                files_processed=progress.indexed_files,
                chunks_created=progress.indexed_chunks,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
                success=False,
                error=str(e),
            )

    async def index_workspace_incremental(
        self,
        workspace_id: str,
        workspace_path: str,
        db,
        tenant_id: Optional[str],
        project_id: str,
        force_reindex: bool = False,
    ) -> IndexingResult:
        """
        증분 인덱싱:
        - workspace_file_index 테이블을 기준으로 변경된 파일만 재인덱싱
        - 삭제된 파일은 vector store에서 삭제 + 메타테이블에서도 제거
        """
        from sqlalchemy import select, delete
        from ..db.models import WorkspaceFileIndexModel

        start_time = datetime.now(timezone.utc)
        progress = IndexingProgress(
            workspace_id=workspace_id,
            status="running",
            started_at=start_time,
        )
        self._progress[workspace_id] = progress

        try:
            if force_reindex:
                await self._vector_store.delete_by_workspace(workspace_id)
                await db.execute(delete(WorkspaceFileIndexModel).where(WorkspaceFileIndexModel.workspace_id == workspace_id))
                await db.commit()

            files = await self.scan_workspace(workspace_path)
            progress.total_files = len(files)

            # 기존 메타 로드
            existing_rows = await db.execute(
                select(WorkspaceFileIndexModel).where(WorkspaceFileIndexModel.workspace_id == workspace_id)
            )
            existing = {r.file_path: r for r in existing_rows.scalars().all()}

            current_paths: Set[str] = set()
            changed_files: List[str] = []

            for file_path in files:
                try:
                    relative_path = str(file_path.relative_to(workspace_path))
                    current_paths.add(relative_path)

                    stat = file_path.stat()
                    mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9))
                    size_bytes = stat.st_size

                    # 빠른 판단: mtime/size가 동일하면 skip
                    prev = existing.get(relative_path)
                    if prev and prev.mtime_ns == mtime_ns and prev.size_bytes == size_bytes:
                        continue

                    # 강한 판단: sha256 비교
                    content = file_path.read_bytes()
                    sha = hashlib.sha256(content).hexdigest()

                    if prev and prev.sha256 == sha:
                        # 내용은 같고 mtime만 바뀐 경우 메타만 갱신
                        prev.mtime_ns = mtime_ns
                        prev.size_bytes = size_bytes
                        continue

                    changed_files.append(relative_path)
                except Exception as e:
                    logger.warning(f"Failed to check file {file_path}: {e}")
                    continue

            # 삭제된 파일 처리
            removed_paths = set(existing.keys()) - current_paths
            for p in removed_paths:
                await self._vector_store.delete_by_file(workspace_id, p)
                await db.execute(
                    delete(WorkspaceFileIndexModel).where(
                        WorkspaceFileIndexModel.workspace_id == workspace_id,
                        WorkspaceFileIndexModel.file_path == p,
                    )
                )

            await db.commit()

            # 변경된 파일 인덱싱
            chunks_created = 0
            for rel in changed_files:
                ok = await self.index_file_with_scope(
                    workspace_id=workspace_id,
                    workspace_path=workspace_path,
                    file_path=rel,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    db=db,
                )
                if ok:
                    progress.indexed_files += 1
                # index_file_with_scope에서 chunk 수를 직접 반환하지 않으므로 대략 누적은 생략

            progress.status = "completed"
            progress.completed_at = datetime.now(timezone.utc)

            duration = (progress.completed_at - start_time).total_seconds()
            return IndexingResult(
                workspace_id=workspace_id,
                files_processed=progress.indexed_files,
                chunks_created=chunks_created,
                duration_seconds=duration,
                success=True,
            )
        except Exception as e:
            logger.error(f"Incremental indexing failed for {workspace_id}: {e}")
            progress.status = "failed"
            progress.error = str(e)
            progress.completed_at = datetime.now(timezone.utc)
            return IndexingResult(
                workspace_id=workspace_id,
                files_processed=progress.indexed_files,
                chunks_created=progress.indexed_chunks,
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(),
                success=False,
                error=str(e),
            )
    
    async def index_file(
        self,
        workspace_id: str,
        workspace_path: str,
        file_path: str,
    ) -> bool:
        """단일 파일 인덱싱 (증분 업데이트)"""
        try:
            full_path = Path(workspace_path) / file_path
            if not full_path.exists():
                logger.warning(f"File not found: {full_path}")
                return False
            
            # 기존 파일 임베딩 삭제
            await self._vector_store.delete_by_file(workspace_id, file_path)
            
            # 파일 읽기 및 청킹
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            chunks = self._chunker.chunk_file(
                content=content,
                file_path=file_path,
                workspace_id=workspace_id,
            )
            
            if not chunks:
                return True
            
            # 임베딩 및 저장
            embedding_results = await self._embedding_service.embed_chunks(chunks)
            
            chunk_ids = [r.chunk_id for r in embedding_results]
            embeddings = [r.embedding for r in embedding_results]
            payloads = [
                {
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "language": chunk.language,
                    "workspace_id": chunk.workspace_id,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ]
            
            await self._vector_store.upsert_embeddings(
                chunk_ids=chunk_ids,
                embeddings=embeddings,
                payloads=payloads,
            )
            
            logger.info(f"Indexed file: {file_path}, chunks={len(chunks)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index file {file_path}: {e}")
            return False

    async def index_file_with_scope(
        self,
        workspace_id: str,
        workspace_path: str,
        file_path: str,
        tenant_id: Optional[str],
        project_id: str,
        db,
    ) -> bool:
        """
        단일 파일 인덱싱 (스코프 포함 + workspace_file_index 메타 갱신)
        """
        from sqlalchemy import select
        from ..db.models import WorkspaceFileIndexModel

        try:
            full_path = Path(workspace_path) / file_path
            if not full_path.exists():
                return False

            # 기존 파일 임베딩 삭제
            await self._vector_store.delete_by_file(workspace_id, file_path)

            content_bytes = full_path.read_bytes()
            sha = hashlib.sha256(content_bytes).hexdigest()
            content = content_bytes.decode("utf-8", errors="ignore")

            chunks = self._chunker.chunk_file(
                content=content,
                file_path=file_path,
                workspace_id=workspace_id,
            )
            if chunks:
                embedding_results = await self._embedding_service.embed_chunks(chunks)
                chunk_ids = [r.chunk_id for r in embedding_results]
                embeddings = [r.embedding for r in embedding_results]
                payloads = [
                    {
                        "content": chunk.content,
                        "file_path": chunk.file_path,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "language": chunk.language,
                        "workspace_id": chunk.workspace_id,
                        "project_id": project_id,
                        "tenant_id": tenant_id,
                        "metadata": chunk.metadata,
                    }
                    for chunk in chunks
                ]
                await self._vector_store.upsert_embeddings(chunk_ids=chunk_ids, embeddings=embeddings, payloads=payloads)

            stat = full_path.stat()
            mtime_ns = getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9))
            size_bytes = stat.st_size

            row = await db.execute(
                select(WorkspaceFileIndexModel).where(
                    WorkspaceFileIndexModel.workspace_id == workspace_id,
                    WorkspaceFileIndexModel.file_path == file_path,
                )
            )
            row = row.scalar_one_or_none()
            if row:
                row.sha256 = sha
                row.mtime_ns = mtime_ns
                row.size_bytes = size_bytes
                row.org_id = tenant_id
                row.project_id = project_id
            else:
                db.add(
                    WorkspaceFileIndexModel(
                        org_id=tenant_id,
                        project_id=project_id,
                        workspace_id=workspace_id,
                        file_path=file_path,
                        sha256=sha,
                        size_bytes=size_bytes,
                        mtime_ns=mtime_ns,
                    )
                )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to index file with scope {file_path}: {e}")
            await db.rollback()
            return False
    
    def get_progress(self, workspace_id: str) -> Optional[IndexingProgress]:
        """인덱싱 진행 상태 조회"""
        return self._progress.get(workspace_id)
    
    async def delete_workspace_index(self, workspace_id: str) -> bool:
        """워크스페이스 인덱스 삭제"""
        try:
            await self._vector_store.delete_by_workspace(workspace_id)
            if workspace_id in self._progress:
                del self._progress[workspace_id]
            logger.info(f"Deleted index for workspace: {workspace_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete workspace index: {e}")
            return False


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_code_indexer: Optional[CodeIndexerService] = None


async def get_code_indexer() -> CodeIndexerService:
    """코드 인덱서 싱글톤 가져오기"""
    global _code_indexer
    if _code_indexer is None:
        _code_indexer = CodeIndexerService()
        await _code_indexer.initialize()
    return _code_indexer
