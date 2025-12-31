"""
Context Collector - 컨텍스트 수집
Task: Context Builder 구현
"""

from typing import List, Dict, Optional
from .models import ContextSource, ContextSourceType


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
            
            # TODO: RELATED, SEARCH 타입은 향후 구현
        
        return collected
    
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
