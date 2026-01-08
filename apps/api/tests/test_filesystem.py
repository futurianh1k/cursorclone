"""
파일시스템 유틸리티 테스트
"""

import pytest
import tempfile
import os
from pathlib import Path
from src.utils.filesystem import (
    get_workspace_root,
    validate_path,
    read_file_content,
    write_file_content,
    build_file_tree,
    create_workspace_directory,
    workspace_exists,
)


class TestWorkspaceRoot:
    """워크스페이스 루트 테스트"""
    
    def test_get_workspace_root_dev_mode(self, monkeypatch):
        """개발 모드 테스트"""
        monkeypatch.setenv("DEV_MODE", "true")
        root = get_workspace_root("demo")
        assert str(root) == "/workspaces/demo"
    
    def test_get_workspace_root_prod_mode(self):
        """운영 모드 테스트"""
        root = get_workspace_root("ws_test")
        assert str(root) == "/workspaces/ws_test"


class TestValidatePath:
    """경로 검증 테스트"""
    
    def test_valid_path(self, tmp_path):
        """정상 경로"""
        result = validate_path("src/main.py", tmp_path)
        assert result == tmp_path / "src" / "main.py"
    
    def test_path_traversal_blocked(self, tmp_path):
        """경로 탈출 차단"""
        with pytest.raises(ValueError, match="Path traversal"):
            validate_path("../etc/passwd", tmp_path)
    
    def test_absolute_path_blocked(self, tmp_path):
        """절대 경로 차단"""
        with pytest.raises(ValueError, match="Absolute paths"):
            validate_path("/etc/passwd", tmp_path)
    
    def test_path_outside_workspace_blocked(self, tmp_path):
        """워크스페이스 외부 경로 차단"""
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        
        # 워크스페이스 외부로 가는 경로는 차단되어야 함
        with pytest.raises(ValueError, match="Path traversal"):
            validate_path("../../outside/file.txt", workspace_root)


class TestFileOperations:
    """파일 읽기/쓰기 테스트"""
    
    def test_read_file_content(self, tmp_path):
        """파일 읽기"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')", encoding="utf-8")
        
        content, encoding = read_file_content(test_file)
        assert content == "print('hello')"
        assert encoding == "utf-8"
    
    def test_read_file_not_found(self, tmp_path):
        """파일 없음"""
        with pytest.raises(FileNotFoundError):
            read_file_content(tmp_path / "nonexistent.py")
    
    def test_write_file_content(self, tmp_path):
        """파일 쓰기"""
        test_file = tmp_path / "test.py"
        write_file_content(test_file, "print('hello')")
        
        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == "print('hello')"
    
    def test_write_file_with_backup(self, tmp_path):
        """백업 생성"""
        test_file = tmp_path / "test.py"
        test_file.write_text("old content", encoding="utf-8")
        
        write_file_content(test_file, "new content", create_backup=True)
        
        backup_file = tmp_path / "test.py.bak"
        assert backup_file.exists()
        assert backup_file.read_text(encoding="utf-8") == "old content"
        assert test_file.read_text(encoding="utf-8") == "new content"


class TestFileTree:
    """파일 트리 테스트"""
    
    def test_build_file_tree(self, tmp_path):
        """파일 트리 생성"""
        # 디렉토리 구조 생성
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "README.md").write_text("# Test")
        
        tree = build_file_tree(tmp_path)
        
        assert len(tree) >= 2
        file_names = [item.name for item in tree]
        assert "src" in file_names or "README.md" in file_names
    
    def test_build_file_tree_excludes_hidden(self, tmp_path):
        """숨김 파일 제외"""
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("test")
        (tmp_path / "README.md").write_text("# Test")
        
        tree = build_file_tree(tmp_path)
        
        # .git은 제외되어야 함
        file_names = [item.name for item in tree]
        assert ".git" not in file_names


class TestWorkspaceManagement:
    """워크스페이스 관리 테스트"""
    
    def test_create_workspace_directory(self, tmp_path):
        """워크스페이스 디렉토리 생성"""
        workspace_root = tmp_path / "workspace"
        create_workspace_directory("test", workspace_root)
        
        assert workspace_root.exists()
        assert workspace_root.is_dir()
    
    def test_workspace_exists(self, tmp_path):
        """워크스페이스 존재 여부"""
        workspace_root = tmp_path / "workspace"
        workspace_root.mkdir()
        
        assert workspace_exists(workspace_root)
        assert not workspace_exists(tmp_path / "nonexistent")
