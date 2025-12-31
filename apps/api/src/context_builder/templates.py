"""
Template Registry - 프롬프트 템플릿 관리
Task: Context Builder 구현
"""

import os
from pathlib import Path
from typing import Dict, Optional
from jinja2 import Template, Environment, FileSystemLoader, select_autoescape


class TemplateRegistry:
    """프롬프트 템플릿 레지스트리"""
    
    def __init__(self, template_dir: Optional[str] = None):
        """
        Template Registry 초기화
        
        Args:
            template_dir: 템플릿 디렉토리 경로 (기본값: packages/prompt-templates)
        """
        if template_dir is None:
            # 프로젝트 루트 기준으로 찾기
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent.parent.parent
            template_dir = str(project_root / "packages" / "prompt-templates")
        
        self.template_dir = Path(template_dir)
        if not self.template_dir.exists():
            raise ValueError(f"Template directory does not exist: {template_dir}")
        
        # Jinja2 환경 설정
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # 캐시
        self._cache: Dict[str, str] = {}
    
    def get_system_prompt(self, action: str) -> str:
        """
        시스템 프롬프트 가져오기
        
        Args:
            action: 액션 타입 (rewrite, explain 등)
            
        Returns:
            시스템 프롬프트 문자열
        """
        # 캐시 확인
        cache_key = f"system:{action}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 템플릿 파일 경로
        template_path = f"system/{action}.md"
        
        # 기본 템플릿이 없으면 base.md 사용
        if not (self.template_dir / template_path).exists():
            template_path = "system/base.md"
        
        # 템플릿 로드
        try:
            template = self.env.get_template(template_path)
            content = template.render()
        except Exception as e:
            # 템플릿 로드 실패 시 기본 메시지
            content = f"You are an AI coding assistant for an enterprise on-prem environment.\n\nAction: {action}"
        
        # 캐시에 저장
        self._cache[cache_key] = content
        
        return content
    
    def build_user_prompt(
        self,
        action: str,
        instruction: str,
        file_path: str,
        content: Optional[str] = None,
        selection: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        사용자 프롬프트 빌드
        
        Args:
            action: 액션 타입
            instruction: 사용자 지시사항
            file_path: 파일 경로
            content: 파일 전체 내용 (선택)
            selection: 선택된 코드 (선택)
            language: 프로그래밍 언어 (선택)
            
        Returns:
            사용자 프롬프트 문자열
        """
        # 언어 자동 감지
        if language is None:
            language = self._detect_language(file_path)
        
        # 프롬프트 구성
        parts = []
        
        # 파일 정보
        parts.append(f"File: {file_path}")
        
        # 선택 범위가 있으면 표시
        if selection:
            parts.append(f"\n```{language}\n{selection}\n```")
        elif content:
            parts.append(f"\n```{language}\n{content}\n```")
        
        # 지시사항
        parts.append(f"\nInstruction: {instruction}")
        
        return "\n".join(parts)
    
    def _detect_language(self, file_path: str) -> str:
        """
        파일 경로에서 언어 감지
        
        Args:
            file_path: 파일 경로
            
        Returns:
            언어 이름 (markdown 코드 블록용)
        """
        ext = Path(file_path).suffix.lower()
        
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".jsx": "jsx",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".cs": "csharp",
            ".sql": "sql",
            ".sh": "bash",
            ".bash": "bash",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".xml": "xml",
        }
        
        return language_map.get(ext, "text")
