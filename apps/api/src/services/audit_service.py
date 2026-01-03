"""
감사 로그 서비스

AGENTS.md 보안 원칙:
- 프롬프트/응답 원문은 저장하지 않음
- 해시 + 메타데이터만 저장
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AuditLogModel
from ..db.connection import get_db

logger = logging.getLogger(__name__)


class AuditService:
    """감사 로그 서비스"""
    
    @staticmethod
    def hash_content(content: str) -> str:
        """
        콘텐츠를 SHA-256 해시로 변환
        
        프롬프트/응답 원문은 저장하지 않고 해시만 저장
        """
        if not content:
            return ""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    @staticmethod
    async def log(
        db: AsyncSession,
        user_id: str,
        workspace_id: str,
        action: str,
        instruction: Optional[str] = None,
        response: Optional[str] = None,
        patch: Optional[str] = None,
        tokens_used: Optional[int] = None,
        request_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
        model: Optional[str] = None,
        status: str = "success",
    ) -> Optional[AuditLogModel]:
        """
        감사 로그 저장
        
        프롬프트/응답 원문은 저장하지 않고 해시만 저장합니다.
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
            workspace_id: 워크스페이스 ID
            action: 수행한 작업 (explain, rewrite, chat, patch_apply 등)
            instruction: 사용자 입력 (해시 저장)
            response: AI 응답 (해시 저장)
            patch: 패치 내용 (해시 저장)
            tokens_used: 사용된 토큰 수
            request_id: 요청 ID
            latency_ms: 응답 시간 (밀리초)
            model: 사용된 모델
            status: 상태 (success, error)
        
        Returns:
            저장된 감사 로그 모델
        """
        try:
            audit_log = AuditLogModel(
                user_id=user_id,
                workspace_id=workspace_id,
                action=action,
                instruction_hash=AuditService.hash_content(instruction) if instruction else None,
                response_hash=AuditService.hash_content(response) if response else None,
                patch_hash=AuditService.hash_content(patch) if patch else None,
                tokens_used=tokens_used,
            )
            
            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)
            
            logger.info(
                f"Audit log saved: user={user_id}, action={action}, "
                f"workspace={workspace_id}, tokens={tokens_used}"
            )
            
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    def log_sync(
        user_id: str,
        action: str,
        model: str,
        request_id: str,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        latency_ms: Optional[float] = None,
        status: str = "success",
    ):
        """
        동기식 감사 로깅 (콘솔 출력용)
        
        DB 연결이 필요 없는 경량 로깅
        AI Gateway 등 빠른 응답이 필요한 곳에서 사용
        """
        audit_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "model": model,
            "request_id": request_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "status": status,
        }
        
        # 콘솔 로깅 (프로덕션에서는 SIEM으로 전송)
        logger.info(f"AUDIT: {audit_log}")


# 싱글톤 인스턴스
audit_service = AuditService()
