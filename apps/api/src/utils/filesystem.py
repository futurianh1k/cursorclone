"""
파일시스템 유틸리티
파일 읽기/쓰기, 디렉토리 트리 생성 등
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Set
from ..models import FileTreeItem, FileType


# 허용된 파일 확장자 (Context Builder와 동일)
ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".java", ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
    ".rb", ".php", ".swift", ".kt", ".scala",
    ".cs", ".vb", ".fs",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".md", ".txt", ".html", ".css", ".scss", ".sass",
    ".xml", ".svg",
    ".sql", ".sh", ".bash", ".zsh", ".fish",
    ".dockerfile", ".dockerignore",
    ".gitignore", ".gitattributes",
    ".env", ".env.example",
}

# 제외할 파일/디렉토리 패턴
EXCLUDE_PATTERNS = {
    ".git",
    ".gitignore",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    ".env",
    ".env.local",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    "*.pyd",
}


def get_workspace_root(workspace_id: str) -> Path:
    """
    워크스페이스 루트 경로 가져오기
    
    Args:
        workspace_id: 워크스페이스 ID
        
    Returns:
        워크스페이스 루트 Path 객체
    """
    # 워크스페이스는 /workspaces/{workspace_id}에 저장
    return Path("/workspaces") / workspace_id


def validate_path(path: str, workspace_root: Path) -> Path:
    """
    경로 검증 및 정규화
    
    Args:
        path: 상대 경로
        workspace_root: 워크스페이스 루트
        
    Returns:
        정규화된 전체 경로
        
    Raises:
        ValueError: 경로 탈출 시도 또는 잘못된 경로
    """
    # 절대 경로 금지
    if os.path.isabs(path):
        raise ValueError("Absolute paths are not allowed")
    
    # 경로 탈출 방지
    if ".." in path or "..\\" in path:
        raise ValueError("Path traversal is not allowed")
    
    # 정규화
    normalized = os.path.normpath(path).replace("\\", "/")
    
    # 전체 경로 구성
    full_path = workspace_root / normalized
    
    # 워크스페이스 내 경로인지 확인
    try:
        resolved = full_path.resolve()
        root_resolved = workspace_root.resolve()
        
        if not str(resolved).startswith(str(root_resolved)):
            raise ValueError("Path outside workspace")
    except Exception as e:
        raise ValueError(f"Invalid path: {e}")
    
    return full_path


def read_file_content(file_path: Path, max_size: int = 10_000_000) -> tuple[str, str]:
    """
    파일 내용 읽기
    
    Args:
        file_path: 파일 경로
        max_size: 최대 파일 크기 (바이트)
        
    Returns:
        (content, encoding) 튜플
        
    Raises:
        FileNotFoundError: 파일 없음
        ValueError: 파일 크기 초과 또는 허용되지 않은 확장자
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise ValueError(f"Not a file: {file_path}")
    
    # 파일 크기 확인
    file_size = file_path.stat().st_size
    if file_size > max_size:
        raise ValueError(f"File too large: {file_size} bytes > {max_size}")
    
    # 확장자 확인
    ext = file_path.suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension not allowed: {ext}")
    
    # 인코딩 감지 및 읽기
    try:
        # UTF-8 시도
        content = file_path.read_text(encoding="utf-8")
        return content, "utf-8"
    except UnicodeDecodeError:
        # UTF-8 실패 시 latin-1 시도 (바이너리 파일은 거부)
        try:
            content = file_path.read_text(encoding="latin-1")
            return content, "latin-1"
        except Exception:
            raise ValueError(f"Cannot decode file: {file_path}")


def write_file_content(file_path: Path, content: str, create_backup: bool = False) -> None:
    """
    파일 내용 쓰기
    
    Args:
        file_path: 파일 경로
        content: 파일 내용
        create_backup: 백업 생성 여부
        
    Raises:
        ValueError: 경로 오류 또는 허용되지 않은 확장자
    """
    # 디렉토리 생성
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 확장자 확인
    ext = file_path.suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extension not allowed: {ext}")
    
    # 백업 생성
    if create_backup and file_path.exists():
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        shutil.copy2(file_path, backup_path)
    
    # 파일 쓰기
    file_path.write_text(content, encoding="utf-8")


def build_file_tree(
    root_path: Path,
    max_depth: int = 10,
    exclude_patterns: Optional[Set[str]] = None,
) -> List[FileTreeItem]:
    """
    파일 트리 생성
    
    Args:
        root_path: 루트 디렉토리 경로
        max_depth: 최대 깊이
        exclude_patterns: 제외할 패턴 (기본값: EXCLUDE_PATTERNS)
        
    Returns:
        파일 트리 아이템 목록
    """
    if exclude_patterns is None:
        exclude_patterns = EXCLUDE_PATTERNS
    
    if not root_path.exists() or not root_path.is_dir():
        return []
    
    items: List[FileTreeItem] = []
    
    def _build_tree(current_path: Path, relative_path: str, depth: int) -> None:
        if depth > max_depth:
            return
        
        try:
            entries = sorted(current_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            
            for entry in entries:
                # 제외 패턴 확인
                if entry.name in exclude_patterns or any(
                    entry.name.endswith(pattern.replace("*", ""))
                    for pattern in exclude_patterns
                    if "*" in pattern
                ):
                    continue
                
                # 숨김 파일 제외 (단, .env.example 등은 허용)
                if entry.name.startswith(".") and entry.name not in {".env.example", ".gitignore"}:
                    continue
                
                relative_entry_path = f"{relative_path}/{entry.name}" if relative_path else entry.name
                
                if entry.is_dir():
                    # 디렉토리
                    children: List[FileTreeItem] = []
                    _build_tree(entry, relative_entry_path, depth + 1)
                    
                    # 하위 항목이 있으면 추가
                    try:
                        sub_entries = list(entry.iterdir())
                        if any(
                            e.name not in exclude_patterns
                            and not (e.name.startswith(".") and e.name not in {".env.example", ".gitignore"})
                            for e in sub_entries
                        ):
                            children = [
                                FileTreeItem(
                                    name=e.name,
                                    path=f"{relative_entry_path}/{e.name}",
                                    type=FileType.FILE if e.is_file() else FileType.DIRECTORY,
                                    children=None if e.is_file() else [],
                                )
                                for e in sorted(sub_entries, key=lambda p: (p.is_file(), p.name.lower()))
                                if e.name not in exclude_patterns
                                and not (e.name.startswith(".") and e.name not in {".env.example", ".gitignore"})
                            ]
                    except PermissionError:
                        pass
                    
                    items.append(
                        FileTreeItem(
                            name=entry.name,
                            path=relative_entry_path,
                            type=FileType.DIRECTORY,
                            children=children if children else None,
                        )
                    )
                elif entry.is_file():
                    # 파일
                    ext = entry.suffix.lower()
                    if not ext or ext in ALLOWED_EXTENSIONS:
                        items.append(
                            FileTreeItem(
                                name=entry.name,
                                path=relative_entry_path,
                                type=FileType.FILE,
                            )
                        )
        except PermissionError:
            pass
    
    _build_tree(root_path, "", 0)
    return items


def create_workspace_directory(workspace_id: str, workspace_root: Path) -> None:
    """
    워크스페이스 디렉토리 생성
    
    Args:
        workspace_id: 워크스페이스 ID
        workspace_root: 워크스페이스 루트 경로
        
    Raises:
        OSError: 디렉토리 생성 실패
    """
    workspace_root.mkdir(parents=True, exist_ok=True)
    
    # 기본 권한 설정 (700: 소유자만 접근)
    os.chmod(workspace_root, 0o700)


def workspace_exists(workspace_root: Path) -> bool:
    """
    워크스페이스 존재 여부 확인
    
    Args:
        workspace_root: 워크스페이스 루트 경로
        
    Returns:
        존재 여부
    """
    return workspace_root.exists() and workspace_root.is_dir()
