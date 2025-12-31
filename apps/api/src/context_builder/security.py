"""
Security Filter - 보안 검증
Task: Context Builder 구현
"""

import os
from typing import List
from pathlib import Path
from .models import ContextSource

# 허용된 파일 확장자 (allowlist)
ALLOWED_EXTENSIONS = {
    # 프로그래밍 언어
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".swift", ".kt", ".scala",
    ".cs", ".vb", ".fs",
    
    # 설정/마크업
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".md", ".txt", ".html", ".css", ".scss", ".sass",
    ".xml", ".svg",
    
    # 기타
    ".sql", ".sh", ".bash", ".zsh", ".fish",
    ".dockerfile", ".dockerignore",
    ".gitignore", ".gitattributes",
    ".env", ".env.example",
}

# 최대 파일 크기 (바이트)
MAX_FILE_SIZE = 10_000_000  # 10MB

# 최대 컨텍스트 크기 (바이트)
MAX_TOTAL_CONTEXT = 500_000  # 500KB


class SecurityError(Exception):
    """보안 검증 오류"""
    pass


class SecurityFilter:
    """보안 필터"""
    
    def __init__(self, workspace_root: str):
        """
        Security Filter 초기화
        
        Args:
            workspace_root: 워크스페이스 루트 경로 (절대 경로)
        """
        self.workspace_root = Path(workspace_root).resolve()
        if not self.workspace_root.exists():
            raise ValueError(f"Workspace root does not exist: {workspace_root}")
    
    async def validate(self, sources: List[ContextSource]) -> List[ContextSource]:
        """
        컨텍스트 소스 보안 검증
        
        Args:
            sources: 검증할 컨텍스트 소스 목록
            
        Returns:
            검증된 컨텍스트 소스 목록
            
        Raises:
            SecurityError: 보안 검증 실패 시
        """
        validated = []
        total_size = 0
        
        for source in sources:
            # 1. 경로 정규화 및 검증
            normalized_path = self._validate_path(source.path)
            
            # 2. 확장자 검증
            self._validate_extension(normalized_path)
            
            # 3. 파일 크기 검증
            if source.content:
                content_size = len(source.content.encode("utf-8"))
                if content_size > MAX_FILE_SIZE:
                    raise SecurityError(
                        f"File too large: {normalized_path} ({content_size} bytes > {MAX_FILE_SIZE})"
                    )
                total_size += content_size
                
                # 크기 제한 초과 시 내용 자르기
                if total_size > MAX_TOTAL_CONTEXT:
                    # 이미 추가된 파일들은 유지하고, 현재 파일만 자르기
                    remaining = MAX_TOTAL_CONTEXT - (total_size - content_size)
                    if remaining > 0:
                        source.content = source.content[:remaining]
                    else:
                        # 더 이상 추가할 수 없음
                        break
            
            # 4. 경로 업데이트
            source.path = normalized_path
            validated.append(source)
        
        return validated
    
    def _validate_path(self, path: str) -> str:
        """
        경로 정규화 및 검증
        
        Args:
            path: 검증할 경로
            
        Returns:
            정규화된 경로
            
        Raises:
            SecurityError: 경로 탈출 시도 감지 시
        """
        # 절대 경로 금지
        if os.path.isabs(path):
            raise SecurityError(f"Absolute paths are not allowed: {path}")
        
        # 경로 탈출 시도 차단
        if ".." in path or "..\\" in path:
            raise SecurityError(f"Path traversal detected: {path}")
        
        # 정규화
        normalized = os.path.normpath(path).replace("\\", "/")
        
        # 다시 한 번 탈출 검증 (정규화 후)
        if ".." in normalized:
            raise SecurityError(f"Path traversal detected after normalization: {normalized}")
        
        # 워크스페이스 내 경로인지 확인
        full_path = (self.workspace_root / normalized).resolve()
        
        # 심볼릭 링크 검증
        real_path = os.path.realpath(str(full_path))
        real_workspace = os.path.realpath(str(self.workspace_root))
        
        if not real_path.startswith(real_workspace):
            raise SecurityError(
                f"Path outside workspace (possibly symlink): {normalized}"
            )
        
        return normalized
    
    def _validate_extension(self, path: str) -> None:
        """
        파일 확장자 검증
        
        Args:
            path: 파일 경로
            
        Raises:
            SecurityError: 허용되지 않은 확장자일 때
        """
        # 확장자 추출
        ext = Path(path).suffix.lower()
        
        # 확장자가 없으면 허용 (디렉토리 등)
        if not ext:
            return
        
        # allowlist 확인
        if ext not in ALLOWED_EXTENSIONS:
            raise SecurityError(
                f"Extension not allowed: {ext} (path: {path})"
            )
