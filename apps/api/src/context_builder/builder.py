"""
Context Builder - 메인 빌더 클래스
Task: Context Builder 구현
"""

import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any
from .models import (
    ContextBuildRequest,
    ContextBuildResponse,
    PromptMessage,
    ActionType,
)
from .security import SecurityFilter
from .templates import TemplateRegistry
from .collector import ContextCollector


class ContextBuilder(ABC):
    """Context Builder 추상 클래스"""
    
    @abstractmethod
    async def build(
        self,
        request: ContextBuildRequest,
    ) -> ContextBuildResponse:
        """컨텍스트를 조합하여 LLM 프롬프트 생성"""
        pass


class DefaultContextBuilder(ContextBuilder):
    """기본 Context Builder 구현"""
    
    def __init__(
        self,
        workspace_root: str,
        template_registry: TemplateRegistry = None,
        security_filter: SecurityFilter = None,
        collector: ContextCollector = None,
    ):
        """
        Context Builder 초기화
        
        Args:
            workspace_root: 워크스페이스 루트 경로
            template_registry: 템플릿 레지스트리 (기본값: 자동 생성)
            security_filter: 보안 필터 (기본값: 자동 생성)
            collector: 컨텍스트 수집기 (기본값: 자동 생성)
        """
        self.workspace_root = workspace_root
        
        # 의존성 주입 또는 자동 생성
        self.templates = template_registry or TemplateRegistry()
        self.security = security_filter or SecurityFilter(workspace_root)
        self.collector = collector or ContextCollector()
    
    async def build(
        self,
        request: ContextBuildRequest,
    ) -> ContextBuildResponse:
        """
        컨텍스트를 조합하여 LLM 프롬프트 생성
        
        Args:
            request: Context Builder 요청
            
        Returns:
            Context Builder 응답 (프롬프트 메시지 + 메타데이터)
        """
        # 1. 보안 필터링
        validated_sources = await self.security.validate(request.sources)
        
        # 2. 컨텍스트 수집
        context = await self.collector.collect(
            validated_sources,
            self.workspace_root,
        )
        
        # 3. 프롬프트 조합
        messages = await self._assemble_prompt(
            action=request.action,
            instruction=request.instruction,
            context=context,
        )
        
        # 4. 메타데이터 생성 (원문 저장 금지)
        metadata = self._create_metadata(request, messages)
        
        return ContextBuildResponse(
            messages=messages,
            metadata=metadata,
        )
    
    async def _assemble_prompt(
        self,
        action: ActionType,
        instruction: str,
        context: Dict[str, Any],
    ) -> list[PromptMessage]:
        """
        프롬프트 조합
        
        Args:
            action: 액션 타입
            instruction: 사용자 지시사항
            context: 수집된 컨텍스트
            
        Returns:
            프롬프트 메시지 목록
        """
        messages = []
        
        # 1. 시스템 프롬프트
        action_str = action.value if hasattr(action, 'value') else str(action)
        system_prompt = self.templates.get_system_prompt(action_str)
        messages.append(PromptMessage(
            role="system",
            content=system_prompt,
        ))
        
        # 2. 사용자 프롬프트 구성
        user_parts = []
        
        # 파일/선택 내용 추가
        if context.get("selections"):
            # 선택된 코드가 있으면 우선 사용
            for sel in context["selections"]:
                file_path = sel["path"]
                content = sel["content"]
                language = self.templates._detect_language(file_path)
                
                user_parts.append(f"File: {file_path} (lines {sel['range'].start_line}-{sel['range'].end_line})")
                user_parts.append(f"```{language}\n{content}\n```")
        
        elif context.get("files"):
            # 전체 파일
            for file_info in context["files"]:
                file_path = file_info["path"]
                content = file_info["content"]
                language = self.templates._detect_language(file_path)
                
                if file_info.get("selection"):
                    # 선택 범위가 있으면 표시
                    range_obj = file_info["selection"]
                    user_parts.append(
                        f"File: {file_path} (lines {range_obj.start_line}-{range_obj.end_line})"
                    )
                    # 선택된 부분만 추출
                    lines = content.split("\n")
                    selected = "\n".join(
                        lines[range_obj.start_line - 1:range_obj.end_line]
                    )
                    user_parts.append(f"```{language}\n{selected}\n```")
                else:
                    user_parts.append(f"File: {file_path}")
                    user_parts.append(f"```{language}\n{content}\n```")
        
        # 지시사항 추가
        user_parts.append(f"\nInstruction: {instruction}")
        
        user_content = "\n\n".join(user_parts)
        messages.append(PromptMessage(
            role="user",
            content=user_content,
        ))
        
        return messages
    
    def _create_metadata(
        self,
        request: ContextBuildRequest,
        messages: list[PromptMessage],
    ) -> Dict[str, Any]:
        """
        메타데이터 생성 (원문 저장 금지, hash만)
        
        Args:
            request: 요청 객체
            messages: 생성된 메시지 목록
            
        Returns:
            메타데이터 딕셔너리
        """
        # 메시지 내용을 문자열로 변환 (해시용)
        messages_str = "\n".join([
            f"{msg.role}: {msg.content}"
            for msg in messages
        ])
        
        # 해시 생성
        context_hash = hashlib.sha256(messages_str.encode("utf-8")).hexdigest()
        instruction_hash = hashlib.sha256(request.instruction.encode("utf-8")).hexdigest()
        
        # 토큰 수 추정 (간단한 방법: 문자 수 / 4)
        total_chars = sum(len(msg.content) for msg in messages)
        tokens_estimate = total_chars // 4
        
        action_str = request.action.value if hasattr(request.action, 'value') else str(request.action)
        return {
            "action": action_str,
            "source_count": len(request.sources),
            "source_paths": [s.path for s in request.sources],
            "total_tokens_estimate": tokens_estimate,
            "context_hash": f"sha256:{context_hash}",
            "instruction_hash": f"sha256:{instruction_hash}",
        }
