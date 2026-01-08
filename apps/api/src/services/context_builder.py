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
from typing import List, Optional, Dict, Any, Literal, Tuple
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
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "3000"))

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
    # 내부 디버깅/진단용(응답 모델에는 노출하지 않음)
    task_type: str = "chat"
    total_tokens_est: int = 0
    
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
        task_type: Optional[str] = None,
        max_context_tokens: Optional[int] = None,
        max_context_chars: Optional[int] = None,
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
        budget_chars = max_context_chars if max_context_chars is not None else MAX_CONTEXT_CHARS
        budget_tokens = max_context_tokens if max_context_tokens is not None else MAX_CONTEXT_TOKENS

        resolved_task_type = task_type or self._classify_task_type(
            query=query,
            current_file=current_file,
            current_file_content=current_file_content,
        )
        
        # 1. 현재 파일 컨텍스트 우선 추가 (작업 유형에 따라 라인 수 조절)
        if current_file and current_file_content:
            current_max_lines = 160 if resolved_task_type in {"bugfix", "refactor"} else 120
            current_ctx = self._create_current_file_context(
                current_file, current_file_content, max_lines=current_max_lines
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
        
        # 4. 작업 유형 + 예산 기반 컨텍스트 팩킹
        packed, total_chars, total_tokens_est, truncated = self._pack_contexts(
            task_type=resolved_task_type,
            current_file=current_file,
            current_file_context=contexts[0] if (contexts and current_file) else None,
            search_results=search_results,
            budget_chars=budget_chars,
            budget_tokens=budget_tokens,
        )
        contexts = packed
        
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
            truncated=truncated,
            task_type=resolved_task_type,
            total_tokens_est=total_tokens_est,
        )
        
        logger.info(
            f"Context built: query='{query[:50]}...', "
            f"task={resolved_task_type}, contexts={len(contexts)}, chars={total_chars}, tokens~={total_tokens_est}, truncated={truncated}"
        )
        
        return result

    def _classify_task_type(
        self,
        query: str,
        current_file: Optional[str],
        current_file_content: Optional[str],
    ) -> str:
        """
        작업 유형 분류(휴리스틱).
        외부 모델 호출 없이, 온프레미스에서도 안정적으로 동작하도록 단순 규칙 기반으로 시작한다.
        """
        q = (query or "").strip().lower()
        if not q:
            return "chat"

        # 명시 키워드 우선
        if any(k in q for k in ["autocomplete", "auto complete", "자동완성", "완성해", "complete this", "suggest"]):
            return "autocomplete"
        if any(k in q for k in ["refactor", "리팩", "정리", "구조", "리네임", "rename", "cleanup"]):
            return "refactor"
        if any(k in q for k in ["bug", "버그", "에러", "error", "exception", "traceback", "stacktrace", "fail", "crash"]):
            return "bugfix"
        if any(k in q for k in ["explain", "설명", "what does", "무슨 뜻", "어떻게 동작"]):
            return "explain"
        if any(k in q for k in ["find", "search", "어디", "찾아", "where is", "grep"]):
            return "search"

        # 짧은 질의 + 현재 파일 존재 => 보통 자동완성/수정 맥락이므로 autocomplete로 가중
        if current_file and current_file_content and len(q) <= 24:
            return "autocomplete"

        return "chat"

    def _estimate_tokens(self, text: str) -> int:
        """
        토큰 수 추정.
        - 가능하면 tiktoken 사용(설치되어 있으면)
        - 아니면 보수적 근사치(4 chars/token)
        """
        if not text:
            return 0
        try:
            import tiktoken  # type: ignore

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            # 근사: 평균 4 chars/token
            return max(1, len(text) // 4)

    def _pack_contexts(
        self,
        task_type: str,
        current_file: Optional[str],
        current_file_context: Optional[CodeContext],
        search_results: List[SearchResult],
        budget_chars: int,
        budget_tokens: int,
    ) -> Tuple[List[CodeContext], int, int, bool]:
        """
        예산 기반 컨텍스트 선택/절단.
        - workspace 규모가 커질수록 “많이 넣기”보다 “정확히 넣기”가 중요하므로
          작업 유형에 따라 파일당 최대 청크 수를 제한하고, 전체 예산을 초과하지 않게 한다.
        """
        packed: List[CodeContext] = []
        total_chars = 0
        total_tokens = 0
        truncated = False

        def can_add(text: str) -> bool:
            nonlocal total_chars, total_tokens
            return (total_chars + len(text) <= budget_chars) and (total_tokens + self._estimate_tokens(text) <= budget_tokens)

        def add_ctx(ctx: CodeContext):
            nonlocal total_chars, total_tokens
            packed.append(ctx)
            total_chars += len(ctx.content)
            total_tokens += self._estimate_tokens(ctx.content)

        # 0) 현재 파일 컨텍스트는 가능하면 유지(최우선)
        if current_file_context and can_add(current_file_context.content):
            add_ctx(current_file_context)
        elif current_file_context:
            # 예산이 너무 작으면 현재 파일도 잘라서 넣는다
            sliced = self._slice_text_to_budget(current_file_context.content, budget_chars=budget_chars, budget_tokens=budget_tokens)
            if sliced:
                ctx2 = CodeContext(
                    file_path=current_file_context.file_path,
                    content=sliced,
                    start_line=current_file_context.start_line,
                    end_line=current_file_context.end_line,
                    language=current_file_context.language,
                    relevance_score=current_file_context.relevance_score,
                )
                add_ctx(ctx2)
                truncated = True

        # 1) 작업 유형별 정책(간단한 v1)
        per_file_max = 2 if task_type in {"bugfix", "refactor"} else 1
        # autocomplete는 “많이”보다 “가까운 것 조금”이 낫다
        if task_type == "autocomplete":
            per_file_max = 1

        # 2) 결과 정렬(점수 우선)
        sorted_results = sorted(search_results, key=lambda r: r.score, reverse=True)

        file_counts: Dict[str, int] = {}
        for r in sorted_results:
            if current_file and r.file_path == current_file:
                continue
            if file_counts.get(r.file_path, 0) >= per_file_max:
                continue

            content = r.content or ""
            if not content:
                continue

            if not can_add(content):
                # 청크를 예산에 맞게 잘라서라도 1개는 넣을 수 있으면 넣는다
                sliced = self._slice_text_to_budget(content, budget_chars=budget_chars - total_chars, budget_tokens=budget_tokens - total_tokens)
                if sliced:
                    packed.append(
                        CodeContext(
                            file_path=r.file_path,
                            content=sliced,
                            start_line=r.start_line,
                            end_line=r.end_line,
                            language=r.language,
                            relevance_score=r.score,
                        )
                    )
                    total_chars += len(sliced)
                    total_tokens += self._estimate_tokens(sliced)
                    file_counts[r.file_path] = file_counts.get(r.file_path, 0) + 1
                    truncated = True
                else:
                    truncated = True
                # 예산이 소진되었으면 중단
                if total_chars >= budget_chars or total_tokens >= budget_tokens:
                    break
                continue

            add_ctx(
                CodeContext(
                    file_path=r.file_path,
                    content=content,
                    start_line=r.start_line,
                    end_line=r.end_line,
                    language=r.language,
                    relevance_score=r.score,
                )
            )
            file_counts[r.file_path] = file_counts.get(r.file_path, 0) + 1

            if total_chars >= budget_chars or total_tokens >= budget_tokens:
                truncated = True
                break

        return packed, total_chars, total_tokens, truncated

    def _slice_text_to_budget(self, text: str, budget_chars: int, budget_tokens: int) -> str:
        """
        예산에 맞게 텍스트를 잘라 반환.
        v1에서는 줄 단위로 자르고, 끝에 truncated 마커를 붙인다.
        """
        if not text:
            return ""
        if budget_chars <= 0 or budget_tokens <= 0:
            return ""

        # truncated 마커까지 고려해서 미리 여유를 남긴다
        marker = "\n... (truncated)"
        effective_chars = max(0, budget_chars - len(marker))

        # 빠른 char 기반 절단(1차)
        hard = text[:effective_chars]
        if not hard:
            return ""

        # 줄 단위로 줄이면서 토큰도 맞춘다
        lines = hard.splitlines()
        out_lines: List[str] = []
        for ln in lines:
            candidate = "\n".join(out_lines + [ln])
            if self._estimate_tokens(candidate) > budget_tokens:
                break
            out_lines.append(ln)

        sliced = "\n".join(out_lines).strip()
        if not sliced:
            return ""
        if not sliced.endswith("... (truncated)"):
            sliced = f"{sliced}{marker}"
        return sliced
    
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
