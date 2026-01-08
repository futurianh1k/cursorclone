"""
Context Builder 서비스
LLM 프롬프트를 위한 관련 코드 컨텍스트 구성

Cursor의 핵심 기능 중 하나인 Context Builder를 구현합니다.
- 사용자 질문에 관련된 코드 청크 검색
- 파일 구조 및 심볼 정보 수집
- 최적화된 프롬프트 컨텍스트 생성

참조:
- Cursor Context: https://www.cursor.com/features
- Continue Codebase: https://docs.continue.dev/features/codebase-embeddings
"""

import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path

from .embedding_service import EmbeddingService, get_embedding_service
from .vector_store import VectorStoreService, SearchResult, get_vector_store

logger = logging.getLogger(__name__)


# ============================================================
# 설정
# ============================================================

# 컨텍스트 크기 제한 (토큰 대략 추정)
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))

# 검색 결과 수
DEFAULT_SEARCH_LIMIT = int(os.getenv("DEFAULT_SEARCH_LIMIT", "10"))

# 유사도 임계값
MIN_SIMILARITY_SCORE = float(os.getenv("MIN_SIMILARITY_SCORE", "0.3"))


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class CodeContext:
    """코드 컨텍스트 조각"""
    file_path: str
    content: str
    start_line: int
    end_line: int
    language: str
    relevance_score: float
    
    def to_prompt_string(self) -> str:
        """프롬프트용 문자열 변환"""
        return f"""### {self.file_path} (lines {self.start_line}-{self.end_line})
```{self.language}
{self.content}
```"""


@dataclass
class FileTreeNode:
    """파일 트리 노드"""
    name: str
    path: str
    is_dir: bool
    children: List["FileTreeNode"] = field(default_factory=list)


@dataclass
class ContextResult:
    """Context Builder 결과"""
    query: str
    workspace_id: str
    contexts: List[CodeContext]
    file_tree: Optional[str] = None
    total_chars: int = 0
    truncated: bool = False
    
    def to_prompt(self) -> str:
        """LLM 프롬프트용 전체 컨텍스트 생성"""
        parts = []
        
        # 파일 트리 (있는 경우)
        if self.file_tree:
            parts.append(f"## Project Structure\n```\n{self.file_tree}\n```\n")
        
        # 관련 코드 컨텍스트
        if self.contexts:
            parts.append("## Relevant Code\n")
            for ctx in self.contexts:
                parts.append(ctx.to_prompt_string())
                parts.append("")
        
        return "\n".join(parts)


# ============================================================
# Context Builder 서비스
# ============================================================

class ContextBuilderService:
    """LLM 컨텍스트 구성 서비스"""
    
    def __init__(self):
        self._embedding_service: Optional[EmbeddingService] = None
        self._vector_store: Optional[VectorStoreService] = None
    
    async def initialize(self):
        """서비스 초기화"""
        self._embedding_service = await get_embedding_service()
        self._vector_store = await get_vector_store()
        logger.info("Context builder initialized")
    
    async def build_context(
        self,
        query: str,
        workspace_id: str,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        workspace_path: Optional[str] = None,
        max_results: int = DEFAULT_SEARCH_LIMIT,
        include_file_tree: bool = False,
        file_filter: Optional[str] = None,
        language_filter: Optional[str] = None,
        current_file: Optional[str] = None,
        current_file_content: Optional[str] = None,
    ) -> ContextResult:
        """
        쿼리에 관련된 코드 컨텍스트 구성
        
        Args:
            query: 사용자 질문/요청
            workspace_id: 워크스페이스 ID
            workspace_path: 워크스페이스 경로 (파일 트리용)
            max_results: 최대 검색 결과 수
            include_file_tree: 파일 트리 포함 여부
            file_filter: 파일 경로 필터
            language_filter: 언어 필터
            current_file: 현재 편집 중인 파일 경로
            current_file_content: 현재 파일 내용
        
        Returns:
            ContextResult: 구성된 컨텍스트
        """
        contexts: List[CodeContext] = []
        total_chars = 0
        
        # 1. 현재 파일 컨텍스트 우선 추가
        if current_file and current_file_content:
            current_ctx = self._create_current_file_context(
                current_file, current_file_content
            )
            if current_ctx:
                contexts.append(current_ctx)
                total_chars += len(current_ctx.content)
        
        # 2. 쿼리 임베딩 생성
        query_embedding = await self._embedding_service.embed_text(query)
        
        # 3. 관련 코드 검색
        search_results = await self._vector_store.search(
            query_embedding=query_embedding,
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            project_id=project_id,
            limit=max_results,
            score_threshold=MIN_SIMILARITY_SCORE,
            file_filter=file_filter,
            language_filter=language_filter,
        )
        
        # 4. 검색 결과를 컨텍스트로 변환
        for result in search_results:
            # 현재 파일과 중복되면 스킵
            if current_file and result.file_path == current_file:
                continue
            
            # 크기 제한 확인
            if total_chars + len(result.content) > MAX_CONTEXT_CHARS:
                break
            
            contexts.append(CodeContext(
                file_path=result.file_path,
                content=result.content,
                start_line=result.start_line,
                end_line=result.end_line,
                language=result.language,
                relevance_score=result.score,
            ))
            total_chars += len(result.content)
        
        # 5. 파일 트리 생성 (선택적)
        file_tree = None
        if include_file_tree and workspace_path:
            file_tree = self._generate_file_tree(workspace_path)
        
        result = ContextResult(
            query=query,
            workspace_id=workspace_id,
            contexts=contexts,
            file_tree=file_tree,
            total_chars=total_chars,
            truncated=total_chars >= MAX_CONTEXT_CHARS,
        )
        
        logger.info(
            f"Context built: query='{query[:50]}...', "
            f"contexts={len(contexts)}, chars={total_chars}"
        )
        
        return result
    
    def _create_current_file_context(
        self,
        file_path: str,
        content: str,
        max_lines: int = 100
    ) -> Optional[CodeContext]:
        """현재 파일 컨텍스트 생성"""
        lines = content.split("\n")
        
        # 파일이 너무 길면 앞부분만
        if len(lines) > max_lines:
            truncated_content = "\n".join(lines[:max_lines])
            truncated_content += f"\n... (truncated, {len(lines) - max_lines} more lines)"
        else:
            truncated_content = content
        
        # 언어 감지
        ext = os.path.splitext(file_path)[1].lower()
        language = self._detect_language(ext)
        
        return CodeContext(
            file_path=file_path,
            content=truncated_content,
            start_line=1,
            end_line=min(len(lines), max_lines),
            language=language,
            relevance_score=1.0,  # 현재 파일은 최고 관련성
        )
    
    def _detect_language(self, extension: str) -> str:
        """확장자로 언어 감지"""
        lang_map = {
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
            ".sql": "sql",
            ".sh": "bash",
            ".html": "html",
            ".css": "css",
        }
        return lang_map.get(extension, "")
    
    def _generate_file_tree(
        self,
        workspace_path: str,
        max_depth: int = 3,
        max_items: int = 50
    ) -> str:
        """파일 트리 문자열 생성"""
        root = Path(workspace_path)
        if not root.exists():
            return ""
        
        lines = []
        item_count = [0]  # 리스트로 감싸서 내부 함수에서 수정 가능하게
        
        def walk(path: Path, prefix: str = "", depth: int = 0):
            if depth > max_depth or item_count[0] >= max_items:
                return
            
            # 무시할 디렉토리
            ignore_dirs = {
                "node_modules", ".git", "__pycache__", ".venv", "venv",
                ".next", "dist", "build", ".idea", ".vscode",
            }
            
            try:
                entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            except PermissionError:
                return
            
            for i, entry in enumerate(entries):
                if item_count[0] >= max_items:
                    lines.append(f"{prefix}└── ... (truncated)")
                    return
                
                if entry.name.startswith(".") and entry.name not in {".env.example"}:
                    continue
                
                if entry.is_dir() and entry.name in ignore_dirs:
                    continue
                
                is_last = i == len(entries) - 1
                connector = "└── " if is_last else "├── "
                
                if entry.is_dir():
                    lines.append(f"{prefix}{connector}{entry.name}/")
                    item_count[0] += 1
                    extension = "    " if is_last else "│   "
                    walk(entry, prefix + extension, depth + 1)
                else:
                    lines.append(f"{prefix}{connector}{entry.name}")
                    item_count[0] += 1
        
        lines.append(f"{root.name}/")
        walk(root)
        
        return "\n".join(lines)
    
    async def get_related_files(
        self,
        query: str,
        workspace_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """관련 파일 목록 조회"""
        query_embedding = await self._embedding_service.embed_text(query)
        
        results = await self._vector_store.search(
            query_embedding=query_embedding,
            workspace_id=workspace_id,
            limit=limit * 2,  # 중복 제거를 위해 더 많이 검색
            score_threshold=MIN_SIMILARITY_SCORE,
        )
        
        # 파일별로 그룹화하고 최고 점수 사용
        file_scores: Dict[str, float] = {}
        for result in results:
            if result.file_path not in file_scores:
                file_scores[result.file_path] = result.score
            else:
                file_scores[result.file_path] = max(
                    file_scores[result.file_path], result.score
                )
        
        # 점수 순 정렬
        sorted_files = sorted(
            file_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"file_path": fp, "relevance_score": score}
            for fp, score in sorted_files
        ]


# ============================================================
# 싱글톤 인스턴스
# ============================================================

_context_builder: Optional[ContextBuilderService] = None


async def get_context_builder() -> ContextBuilderService:
    """Context Builder 싱글톤 가져오기"""
    global _context_builder
    if _context_builder is None:
        _context_builder = ContextBuilderService()
        await _context_builder.initialize()
    return _context_builder
