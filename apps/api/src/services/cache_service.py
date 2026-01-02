"""
캐시 서비스
Redis 기반 캐싱 레이어
대규모 스케일링을 위한 성능 최적화
"""

import json
import os
from typing import Optional, Any
import redis.asyncio as redis
from datetime import timedelta

# Redis 연결 설정
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_POOL_SIZE = int(os.getenv("REDIS_POOL_SIZE", "10"))


class CacheService:
    """Redis 기반 캐시 서비스"""
    
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self):
        """Redis 연결 초기화"""
        if self._redis is None:
            self._pool = redis.ConnectionPool.from_url(
                REDIS_URL,
                max_connections=REDIS_POOL_SIZE,
                decode_responses=True,
            )
            self._redis = redis.Redis(connection_pool=self._pool)
    
    async def disconnect(self):
        """Redis 연결 종료"""
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        if not self._redis:
            await self.connect()
        
        value = await self._redis.get(key)
        if value is None:
            return None
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ):
        """캐시에 값 저장"""
        if not self._redis:
            await self.connect()
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        if ttl:
            await self._redis.setex(key, ttl, value)
        else:
            await self._redis.set(key, value)
    
    async def delete(self, key: str):
        """캐시에서 값 삭제"""
        if not self._redis:
            await self.connect()
        
        await self._redis.delete(key)
    
    async def delete_pattern(self, pattern: str):
        """패턴에 맞는 키 삭제"""
        if not self._redis:
            await self.connect()
        
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)
    
    # 워크스페이스 관련 캐시 헬퍼 메서드
    
    async def get_workspace_list(self, user_id: str) -> Optional[list]:
        """사용자의 워크스페이스 목록 캐시 조회"""
        return await self.get(f"workspace:list:{user_id}")
    
    async def set_workspace_list(self, user_id: str, workspaces: list, ttl: int = 300):
        """워크스페이스 목록 캐시 저장 (5분 TTL)"""
        await self.set(f"workspace:list:{user_id}", workspaces, ttl=ttl)
    
    async def invalidate_workspace_list(self, user_id: str):
        """워크스페이스 목록 캐시 무효화"""
        await self.delete(f"workspace:list:{user_id}")
    
    async def get_file_tree(self, workspace_id: str) -> Optional[dict]:
        """파일 트리 캐시 조회"""
        return await self.get(f"workspace:tree:{workspace_id}")
    
    async def set_file_tree(self, workspace_id: str, tree: dict, ttl: int = 60):
        """파일 트리 캐시 저장 (1분 TTL)"""
        await self.set(f"workspace:tree:{workspace_id}", tree, ttl=ttl)
    
    async def invalidate_file_tree(self, workspace_id: str):
        """파일 트리 캐시 무효화"""
        await self.delete(f"workspace:tree:{workspace_id}")
        # 패턴으로 관련 캐시도 삭제
        await self.delete_pattern(f"workspace:tree:{workspace_id}:*")


# 전역 인스턴스
cache_service = CacheService()
