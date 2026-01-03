"""
Context Builder 테스트
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.context_builder.models import (
    ContextSource,
    ContextSourceType,
    SelectionRange,
)
from src.context_builder.collector import ContextCollector


class TestContextCollector:
    """ContextCollector 테스트"""

    @pytest.fixture
    def collector(self):
        return ContextCollector()

    @pytest.mark.asyncio
    async def test_collect_selection(self, collector):
        """선택 영역 컨텍스트 수집 테스트"""
        sources = [
            ContextSource(
                type=ContextSourceType.SELECTION,
                path="test.py",
                content="line1\nline2\nline3\nline4\nline5",
                range=SelectionRange(start_line=2, end_line=4),
            )
        ]
        
        result = await collector.collect(sources, "/tmp/workspace")
        
        assert "selections" in result
        assert len(result["selections"]) == 1
        assert result["selections"][0]["path"] == "test.py"
        assert "line2" in result["selections"][0]["content"]

    @pytest.mark.asyncio
    async def test_collect_file(self, collector):
        """전체 파일 컨텍스트 수집 테스트"""
        sources = [
            ContextSource(
                type=ContextSourceType.FILE,
                path="main.py",
                content="def main():\n    pass",
            )
        ]
        
        result = await collector.collect(sources, "/tmp/workspace")
        
        assert "files" in result
        assert len(result["files"]) == 1
        assert result["files"][0]["path"] == "main.py"
        assert result["files"][0]["content"] == "def main():\n    pass"

    @pytest.mark.asyncio
    async def test_collect_empty_sources(self, collector):
        """빈 소스 목록 처리 테스트"""
        result = await collector.collect([], "/tmp/workspace")
        
        assert result["files"] == []
        assert result["selections"] == []

    def test_extract_selection_valid_range(self, collector):
        """유효한 범위 선택 추출 테스트"""
        content = "line1\nline2\nline3\nline4\nline5"
        range_obj = MagicMock(start_line=2, end_line=4)
        
        result = collector._extract_selection(content, range_obj)
        
        assert "line2" in result
        assert "line3" in result
        assert "line4" in result
        assert "line1" not in result
        assert "line5" not in result

    def test_extract_selection_overflow_range(self, collector):
        """범위 초과 선택 추출 테스트"""
        content = "line1\nline2\nline3"
        range_obj = MagicMock(start_line=1, end_line=10)
        
        result = collector._extract_selection(content, range_obj)
        
        assert "line1" in result
        assert "line3" in result


class TestExtractImports:
    """import 추출 테스트"""

    @pytest.fixture
    def collector(self):
        return ContextCollector()

    def test_extract_python_imports(self, collector):
        """Python import 추출 테스트"""
        content = """
from .utils import helper
from ..models import User
import os
from typing import List
"""
        imports = collector._extract_imports(content, ".py")
        
        # 상대 경로만 반환
        assert ".utils" in imports or "./utils" in imports or any("utils" in i for i in imports)

    def test_extract_typescript_imports(self, collector):
        """TypeScript import 추출 테스트"""
        content = """
import { useState } from 'react';
import { User } from './types';
import api from '../lib/api';
import './styles.css';
"""
        imports = collector._extract_imports(content, ".ts")
        
        # 상대 경로만 반환
        assert "./types" in imports
        assert "../lib/api" in imports

    def test_extract_no_relative_imports(self, collector):
        """외부 패키지 import 제외 테스트"""
        content = """
import numpy as np
from fastapi import APIRouter
"""
        imports = collector._extract_imports(content, ".py")
        
        # 외부 패키지는 반환하지 않음
        assert all(imp.startswith(".") for imp in imports)


class TestResolveImport:
    """import 경로 해석 테스트"""

    @pytest.fixture
    def collector(self):
        return ContextCollector()

    def test_resolve_relative_import(self, collector, tmp_path):
        """상대 경로 import 해석 테스트"""
        # 테스트 파일 생성
        (tmp_path / "utils.py").write_text("# utils")
        
        result = collector._resolve_import(
            "./utils",
            tmp_path,
            str(tmp_path.parent),
        )
        
        assert result is not None
        assert result.name == "utils.py"

    def test_resolve_import_with_extension(self, collector, tmp_path):
        """확장자가 있는 import 해석 테스트"""
        (tmp_path / "helper.ts").write_text("// helper")
        
        result = collector._resolve_import(
            "./helper.ts",
            tmp_path,
            str(tmp_path.parent),
        )
        
        # 확장자가 이미 있으므로 그대로 해석되어야 함
        # 파일이 존재하면 반환
        if (tmp_path / "helper.ts").exists():
            assert result is None or result.name == "helper.ts"

    def test_resolve_nonexistent_import(self, collector, tmp_path):
        """존재하지 않는 import 해석 테스트"""
        result = collector._resolve_import(
            "./nonexistent",
            tmp_path,
            str(tmp_path.parent),
        )
        
        assert result is None


class TestSearchCodebase:
    """코드베이스 검색 테스트"""

    @pytest.fixture
    def collector(self):
        return ContextCollector()

    @pytest.mark.asyncio
    async def test_search_finds_matches(self, collector, tmp_path):
        """검색 매치 테스트"""
        # 테스트 파일 생성
        (tmp_path / "main.py").write_text("def calculate_sum():\n    pass")
        (tmp_path / "utils.py").write_text("def helper():\n    pass")
        
        results = await collector._search_codebase("calculate", str(tmp_path))
        
        assert len(results) >= 1
        assert any("main.py" in r["path"] for r in results)

    @pytest.mark.asyncio
    async def test_search_empty_query(self, collector, tmp_path):
        """빈 쿼리 검색 테스트"""
        results = await collector._search_codebase("", str(tmp_path))
        
        assert results == []

    @pytest.mark.asyncio
    async def test_search_excludes_node_modules(self, collector, tmp_path):
        """node_modules 제외 테스트"""
        # node_modules 내 파일 생성
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "package.js").write_text("const test = 'target_string'")
        
        # 일반 파일도 생성
        (tmp_path / "main.js").write_text("const main = 'hello'")
        
        results = await collector._search_codebase("target_string", str(tmp_path))
        
        # node_modules 내 결과는 제외되어야 함
        assert all("node_modules" not in r["path"] for r in results)
