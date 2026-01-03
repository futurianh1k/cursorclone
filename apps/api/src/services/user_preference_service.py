"""
사용자 선호도 서비스

Redis 기반 사용자 선호도 저장 및 조회:
- 마지막 선택 서버
- 최근 사용 워크스페이스
- UI 설정
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
PREFERENCE_TTL = 86400 * 30  # 30일


class UserPreferenceService:
    """사용자 선호도 서비스"""
    
    def __init__(self):
        self._client = None
    
    async def _get_client(self):
        """Redis 클라이언트 가져오기 (lazy init)"""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(REDIS_URL, decode_responses=True)
            except ImportError:
                logger.warning("redis library not installed")
                return None
        return self._client
    
    # ============================================================
    # 마지막 선택 서버
    # ============================================================
    
    async def get_last_selected_server(self, user_id: str) -> Optional[str]:
        """
        마지막 선택 서버 ID 조회
        
        Returns:
            서버 ID (UUID 문자열) 또는 None
        """
        client = await self._get_client()
        if not client:
            return None
        
        try:
            server_id = await client.get(f"pref:{user_id}:last_server")
            return server_id
        except Exception as e:
            logger.warning(f"Failed to get last selected server: {e}")
            return None
    
    async def set_last_selected_server(self, user_id: str, server_id: str):
        """
        마지막 선택 서버 저장
        """
        client = await self._get_client()
        if not client:
            return
        
        try:
            await client.set(
                f"pref:{user_id}:last_server",
                server_id,
                ex=PREFERENCE_TTL,
            )
        except Exception as e:
            logger.warning(f"Failed to set last selected server: {e}")
    
    # ============================================================
    # 최근 사용 워크스페이스
    # ============================================================
    
    async def get_recent_workspaces(
        self, user_id: str, limit: int = 5
    ) -> List[str]:
        """
        최근 사용 워크스페이스 목록 조회
        
        Returns:
            워크스페이스 ID 목록 (최신 순)
        """
        client = await self._get_client()
        if not client:
            return []
        
        try:
            # Sorted Set에서 최신 순으로 조회
            workspaces = await client.zrevrange(
                f"pref:{user_id}:recent_workspaces",
                0, limit - 1,
            )
            return workspaces
        except Exception as e:
            logger.warning(f"Failed to get recent workspaces: {e}")
            return []
    
    async def add_recent_workspace(self, user_id: str, workspace_id: str):
        """
        최근 사용 워크스페이스 추가
        """
        client = await self._get_client()
        if not client:
            return
        
        try:
            timestamp = datetime.now(timezone.utc).timestamp()
            
            # Sorted Set에 추가 (score = timestamp)
            await client.zadd(
                f"pref:{user_id}:recent_workspaces",
                {workspace_id: timestamp},
            )
            
            # 최대 20개 유지
            await client.zremrangebyrank(
                f"pref:{user_id}:recent_workspaces",
                0, -21,
            )
            
            # TTL 갱신
            await client.expire(
                f"pref:{user_id}:recent_workspaces",
                PREFERENCE_TTL,
            )
        except Exception as e:
            logger.warning(f"Failed to add recent workspace: {e}")
    
    # ============================================================
    # UI 설정
    # ============================================================
    
    async def get_ui_settings(self, user_id: str) -> Dict[str, Any]:
        """
        UI 설정 조회
        
        Returns:
            설정 딕셔너리
        """
        client = await self._get_client()
        if not client:
            return {}
        
        try:
            settings_json = await client.get(f"pref:{user_id}:ui_settings")
            if settings_json:
                return json.loads(settings_json)
            return {}
        except Exception as e:
            logger.warning(f"Failed to get UI settings: {e}")
            return {}
    
    async def set_ui_settings(self, user_id: str, settings: Dict[str, Any]):
        """
        UI 설정 저장
        """
        client = await self._get_client()
        if not client:
            return
        
        try:
            await client.set(
                f"pref:{user_id}:ui_settings",
                json.dumps(settings),
                ex=PREFERENCE_TTL,
            )
        except Exception as e:
            logger.warning(f"Failed to set UI settings: {e}")
    
    async def update_ui_setting(self, user_id: str, key: str, value: Any):
        """
        개별 UI 설정 업데이트
        """
        settings = await self.get_ui_settings(user_id)
        settings[key] = value
        await self.set_ui_settings(user_id, settings)
    
    # ============================================================
    # 일괄 조회
    # ============================================================
    
    async def get_all_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        모든 선호도 일괄 조회
        """
        last_server = await self.get_last_selected_server(user_id)
        recent_workspaces = await self.get_recent_workspaces(user_id)
        ui_settings = await self.get_ui_settings(user_id)
        
        return {
            "last_selected_server": last_server,
            "recent_workspaces": recent_workspaces,
            "ui_settings": ui_settings,
        }
    
    async def close(self):
        """클라이언트 연결 종료"""
        if self._client:
            await self._client.close()
            self._client = None


# 싱글톤 인스턴스
user_preference_service = UserPreferenceService()


# FastAPI 의존성
async def get_preference_service() -> UserPreferenceService:
    return user_preference_service
