"""
Context Collector - 컨텍스트 수집
Task: Context Builder 구현

RELATED 타입: 현재 파일과 관련된 파일 자동 수집
- import/require 분석
- 동일 디렉토리 파일
- 테스트 파일 연결

SEARCH 타입: 코드베이스 검색
- 키워드 검색
- 심볼 검색
- 정규식 검색
"""

import os
import re
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from .models import ContextSource, ContextSourceType

logger = logging.getLogger(__name__)


class ContextCollector:
    """컨텍스트 수집기"""
    
    async def collect(
        self,
        sources: List[ContextSource],
        workspace_root: str,
    ) -> Dict[str, any]:
        """
        컨텍스트 소스에서 실제 내용 수집
        
        Args:
            sources: 검증된 컨텍스트 소스 목록
            workspace_root: 워크스페이스 루트 경로
            
        Returns:
            수집된 컨텍스트 딕셔너리
            {
                "files": [
                    {
                        "path": "src/main.py",
                        "content": "...",
                        "selection": {...}  # 선택 범위가 있는 경우
                    }
                ],
                "selections": [...]  # 선택된 코드만
            }
        """
        collected = {
            "files": [],
            "selections": [],
        }
        
        for source in sources:
            if source.type == ContextSourceType.SELECTION:
                # 선택된 코드만
                if source.content and source.range:
                    selection_content = self._extract_selection(
                        source.content,
                        source.range,
                    )
                    collected["selections"].append({
                        "path": source.path,
                        "content": selection_content,
                        "range": source.range,
                    })
            
            elif source.type == ContextSourceType.FILE:
                # 전체 파일
                if source.content:
                    collected["files"].append({
                        "path": source.path,
                        "content": source.content,
                        "selection": source.range if source.range else None,
                    })
            
            elif source.type == ContextSourceType.RELATED:
                # 관련 파일 수집
                related_files = await self._collect_related_files(
                    source.path,
                    source.content,
                    workspace_root,
                )
                collected["files"].extend(related_files)
            
            elif source.type == ContextSourceType.SEARCH:
                # 코드베이스 검색
                if source.content:  # content를 검색 쿼리로 사용
                    search_results = await self._search_codebase(
                        source.content,
                        workspace_root,
                    )
                    collected["files"].extend(search_results)
        
        return collected
    
    async def _collect_related_files(
        self,
        file_path: str,
        content: Optional[str],
        workspace_root: str,
    ) -> List[Dict[str, Any]]:
        """
        현재 파일과 관련된 파일 수집
        
        전략:
        1. import/require 분석하여 의존 파일 찾기
        2. 동일 디렉토리의 관련 파일 (index, types, utils 등)
        3. 테스트 파일 연결
        """
        related_files = []
        
        if not file_path:
            return related_files
        
        full_path = Path(workspace_root) / file_path
        file_dir = full_path.parent
        file_ext = full_path.suffix
        file_stem = full_path.stem
        
        # 1. import/require 분석
        if content:
            imports = self._extract_imports(content, file_ext)
            for import_path in imports:
                resolved_path = self._resolve_import(import_path, file_dir, workspace_root)
                if resolved_path:
                    try:
                        import_content = await self._read_file(resolved_path)
                        if import_content:
                            related_files.append({
                                "path": str(resolved_path.relative_to(workspace_root)),
                                "content": import_content,
                                "relation": "import",
                            })
                    except Exception as e:
                        logger.debug(f"Failed to read import {resolved_path}: {e}")
        
        # 2. 동일 디렉토리의 관련 파일
        related_names = ["index", "types", "utils", "constants", "helpers"]
        for name in related_names:
            for ext in [file_ext, ".ts", ".js", ".py"]:
                related_path = file_dir / f"{name}{ext}"
                if related_path.exists() and related_path != full_path:
                    try:
                        rel_content = await self._read_file(related_path)
                        if rel_content:
                            related_files.append({
                                "path": str(related_path.relative_to(workspace_root)),
                                "content": rel_content,
                                "relation": "sibling",
                            })
                    except Exception:
                        pass
        
        # 3. 테스트 파일 연결
        test_patterns = [
            file_dir / f"{file_stem}.test{file_ext}",
            file_dir / f"{file_stem}.spec{file_ext}",
            file_dir / "__tests__" / f"{file_stem}{file_ext}",
            file_dir.parent / "tests" / f"test_{file_stem}{file_ext}",
        ]
        for test_path in test_patterns:
            if test_path.exists():
                try:
                    test_content = await self._read_file(test_path)
                    if test_content:
                        related_files.append({
                            "path": str(test_path.relative_to(workspace_root)),
                            "content": test_content,
                            "relation": "test",
                        })
                except Exception:
                    pass
        
        # 최대 5개로 제한
        return related_files[:5]
    
    def _extract_imports(self, content: str, file_ext: str) -> List[str]:
        """파일 내용에서 import 경로 추출"""
        imports = []
        
        if file_ext in [".py"]:
            # Python imports
            # from xxx import yyy
            # import xxx
            patterns = [
                r'^from\s+([.\w]+)\s+import',
                r'^import\s+([.\w]+)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                imports.extend(matches)
        
        elif file_ext in [".ts", ".tsx", ".js", ".jsx"]:
            # JavaScript/TypeScript imports
            # import xxx from 'yyy'
            # import 'yyy'
            # require('yyy')
            patterns = [
                r"import\s+.*?from\s+['\"]([^'\"]+)['\"]",
                r"import\s+['\"]([^'\"]+)['\"]",
                r"require\(['\"]([^'\"]+)['\"]\)",
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)
        
        # 상대 경로만 반환 (외부 패키지 제외)
        return [imp for imp in imports if imp.startswith(".")]
    
    def _resolve_import(
        self, import_path: str, current_dir: Path, workspace_root: str
    ) -> Optional[Path]:
        """import 경로를 실제 파일 경로로 해석"""
        # 상대 경로 해석
        if import_path.startswith("./"):
            base_path = current_dir / import_path[2:]
        elif import_path.startswith("../"):
            base_path = current_dir / import_path
        else:
            # 절대 경로 또는 패키지
            return None
        
        # 확장자 추가 시도
        extensions = [".ts", ".tsx", ".js", ".jsx", ".py", "/index.ts", "/index.js"]
        
        # 이미 확장자가 있으면 그대로
        if base_path.suffix:
            if base_path.exists():
                return base_path
            return None
        
        # 확장자 추가 시도
        for ext in extensions:
            full_path = Path(str(base_path) + ext)
            if full_path.exists():
                return full_path
        
        return None
    
    async def _search_codebase(
        self,
        query: str,
        workspace_root: str,
    ) -> List[Dict[str, Any]]:
        """
        코드베이스 검색
        
        검색 전략:
        1. 정확한 문자열 매칭
        2. 심볼 검색 (함수명, 클래스명 등)
        3. 파일명 검색
        """
        results = []
        
        if not query:
            return results
        
        workspace_path = Path(workspace_root)
        
        # 검색할 확장자
        search_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}
        
        # 제외할 디렉토리
        exclude_dirs = {"node_modules", ".git", "__pycache__", ".next", "dist", "build", ".venv", "venv"}
        
        try:
            for root, dirs, files in os.walk(workspace_path):
                # 제외할 디렉토리 필터링
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for filename in files:
                    file_path = Path(root) / filename
                    
                    # 확장자 필터
                    if file_path.suffix not in search_extensions:
                        continue
                    
                    try:
                        content = await self._read_file(file_path)
                        if content and query.lower() in content.lower():
                            # 매칭된 라인 찾기
                            matching_lines = []
                            for i, line in enumerate(content.split("\n"), 1):
                                if query.lower() in line.lower():
                                    matching_lines.append({
                                        "line": i,
                                        "content": line.strip()[:100],
                                    })
                            
                            results.append({
                                "path": str(file_path.relative_to(workspace_path)),
                                "content": content[:2000],  # 처음 2000자만
                                "matches": matching_lines[:5],  # 처음 5개 매치
                                "relation": "search",
                            })
                            
                            # 최대 10개 결과
                            if len(results) >= 10:
                                return results
                    
                    except Exception as e:
                        logger.debug(f"Search error for {file_path}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Codebase search failed: {e}")
        
        return results
    
    async def _read_file(self, file_path: Path) -> Optional[str]:
        """파일 읽기 (비동기)"""
        try:
            # aiofiles가 없으면 동기로 읽기
            try:
                import aiofiles
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    return await f.read()
            except ImportError:
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception as e:
            logger.debug(f"Failed to read file {file_path}: {e}")
            return None
    
    def _extract_selection(
        self,
        content: str,
        range_obj,
    ) -> str:
        """
        선택 범위에 해당하는 코드 추출
        
        Args:
            content: 전체 파일 내용
            range_obj: 선택 범위
            
        Returns:
            선택된 코드
        """
        lines = content.split("\n")
        
        # 0-based 인덱스로 변환
        start_idx = range_obj.start_line - 1
        end_idx = range_obj.end_line
        
        # 범위 검증
        if start_idx < 0:
            start_idx = 0
        if end_idx > len(lines):
            end_idx = len(lines)
        
        # 선택된 라인 추출
        selected_lines = lines[start_idx:end_idx]
        
        return "\n".join(selected_lines)
