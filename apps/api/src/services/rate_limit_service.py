"""
Rate Limiting 서비스

로그인 시도, API 요청 등에 대한 속도 제한

참조:
- Token Bucket 알고리즘
- Redis 기반 분산 Rate Limiting
"""

import os
import time
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


class InMemoryRateLimiter:
    """
    인메모리 Rate Limiter (단일 인스턴스용)
    
    프로덕션에서는 Redis 기반 Rate Limiter 사용 권장
    """
    
    def __init__(self):
        # {key: [(timestamp, count), ...]}
        self._attempts: dict = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(
        self,
        key: str,
        max_attempts: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """
        Rate Limit 확인
        
        Args:
            key: Rate Limit 키 (예: "login:user@example.com", "api:192.168.1.1")
            max_attempts: 윈도우 내 최대 시도 횟수
            window_seconds: 윈도우 크기 (초)
        
        Returns:
            (allowed, remaining, reset_after)
            - allowed: 허용 여부
            - remaining: 남은 시도 횟수
            - reset_after: 리셋까지 남은 시간 (초)
        """
        async with self._lock:
            now = time.time()
            window_start = now - window_seconds
            
            # 윈도우 내 시도만 유지
            self._attempts[key] = [
                ts for ts in self._attempts[key]
                if ts > window_start
            ]
            
            current_attempts = len(self._attempts[key])
            remaining = max(0, max_attempts - current_attempts)
            
            if current_attempts >= max_attempts:
                # 가장 오래된 시도가 리셋되는 시간
                oldest = min(self._attempts[key]) if self._attempts[key] else now
                reset_after = int(oldest + window_seconds - now)
                return False, 0, max(1, reset_after)
            
            return True, remaining, 0
    
    async def record_attempt(self, key: str):
        """시도 기록"""
        async with self._lock:
            self._attempts[key].append(time.time())
    
    async def reset(self, key: str):
        """특정 키의 Rate Limit 리셋"""
        async with self._lock:
            if key in self._attempts:
                del self._attempts[key]
    
    async def cleanup(self):
        """오래된 항목 정리"""
        async with self._lock:
            now = time.time()
            # 1시간 이상 된 항목 정리
            cutoff = now - 3600
            for key in list(self._attempts.keys()):
                self._attempts[key] = [
                    ts for ts in self._attempts[key]
                    if ts > cutoff
                ]
                if not self._attempts[key]:
                    del self._attempts[key]


class RedisRateLimiter:
    """
    Redis 기반 Rate Limiter (분산 환경용)
    
    Sliding Window 알고리즘 사용
    """
    
    def __init__(self):
        self._client = None
    
    async def _get_client(self):
        """Redis 클라이언트 가져오기"""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.from_url(REDIS_URL, decode_responses=True)
            except ImportError:
                logger.warning("redis library not installed, falling back to in-memory")
                return None
        return self._client
    
    async def check_rate_limit(
        self,
        key: str,
        max_attempts: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """
        Rate Limit 확인 (Redis)
        
        Sliding Window Log 알고리즘 사용
        """
        client = await self._get_client()
        if not client:
            # Redis 없으면 허용
            return True, max_attempts, 0
        
        try:
            now = time.time()
            window_start = now - window_seconds
            redis_key = f"ratelimit:{key}"
            
            # 트랜잭션으로 원자적 처리
            async with client.pipeline() as pipe:
                # 윈도우 외 항목 제거
                await pipe.zremrangebyscore(redis_key, 0, window_start)
                # 현재 카운트
                await pipe.zcard(redis_key)
                # TTL 설정
                await pipe.expire(redis_key, window_seconds * 2)
                results = await pipe.execute()
            
            current_attempts = results[1]
            remaining = max(0, max_attempts - current_attempts)
            
            if current_attempts >= max_attempts:
                # 가장 오래된 시도 시간 조회
                oldest = await client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    reset_after = int(oldest[0][1] + window_seconds - now)
                    return False, 0, max(1, reset_after)
                return False, 0, window_seconds
            
            return True, remaining, 0
            
        except Exception as e:
            logger.warning(f"Redis rate limit check failed: {e}")
            return True, max_attempts, 0
    
    async def record_attempt(self, key: str):
        """시도 기록 (Redis)"""
        client = await self._get_client()
        if not client:
            return
        
        try:
            now = time.time()
            redis_key = f"ratelimit:{key}"
            # Sorted Set에 추가 (score = timestamp)
            await client.zadd(redis_key, {str(now): now})
        except Exception as e:
            logger.warning(f"Redis rate limit record failed: {e}")
    
    async def reset(self, key: str):
        """Rate Limit 리셋"""
        client = await self._get_client()
        if not client:
            return
        
        try:
            await client.delete(f"ratelimit:{key}")
        except Exception as e:
            logger.warning(f"Redis rate limit reset failed: {e}")


class RateLimitService:
    """
    Rate Limiting 서비스
    
    다양한 Rate Limit 정책 지원:
    - 로그인 시도 제한
    - API 요청 제한
    - IP 기반 제한
    """
    
    # Rate Limit 정책
    POLICIES = {
        "login": {"max_attempts": 5, "window_seconds": 300},      # 5분에 5회
        "login_ip": {"max_attempts": 20, "window_seconds": 300},  # IP당 5분에 20회
        "signup": {"max_attempts": 3, "window_seconds": 3600},    # 1시간에 3회
        "password_reset": {"max_attempts": 3, "window_seconds": 3600},
        "api": {"max_attempts": 100, "window_seconds": 60},       # 분당 100회
        "api_heavy": {"max_attempts": 10, "window_seconds": 60},  # 분당 10회 (AI 등)
    }
    
    def __init__(self, use_redis: bool = True):
        """
        Args:
            use_redis: Redis 사용 여부 (False면 인메모리)
        """
        self.use_redis = use_redis
        self._redis_limiter = RedisRateLimiter() if use_redis else None
        self._memory_limiter = InMemoryRateLimiter()
    
    async def check_login_rate_limit(
        self,
        email: str,
        ip_address: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        로그인 Rate Limit 확인
        
        Returns:
            (allowed, message)
        """
        policy = self.POLICIES["login"]
        key = f"login:{email}"
        
        limiter = self._redis_limiter if self.use_redis else self._memory_limiter
        allowed, remaining, reset_after = await limiter.check_rate_limit(
            key,
            policy["max_attempts"],
            policy["window_seconds"],
        )
        
        if not allowed:
            return False, f"Too many login attempts. Try again in {reset_after} seconds."
        
        # IP 기반 추가 체크
        if ip_address:
            ip_policy = self.POLICIES["login_ip"]
            ip_key = f"login_ip:{ip_address}"
            ip_allowed, _, ip_reset = await limiter.check_rate_limit(
                ip_key,
                ip_policy["max_attempts"],
                ip_policy["window_seconds"],
            )
            if not ip_allowed:
                return False, f"Too many login attempts from this IP. Try again in {ip_reset} seconds."
        
        return True, ""
    
    async def record_login_attempt(
        self,
        email: str,
        ip_address: Optional[str] = None,
        success: bool = False,
    ):
        """
        로그인 시도 기록
        
        성공 시 해당 이메일의 Rate Limit 리셋
        """
        limiter = self._redis_limiter if self.use_redis else self._memory_limiter
        
        if success:
            # 성공 시 리셋
            await limiter.reset(f"login:{email}")
        else:
            # 실패 시 기록
            await limiter.record_attempt(f"login:{email}")
            if ip_address:
                await limiter.record_attempt(f"login_ip:{ip_address}")
    
    async def check_api_rate_limit(
        self,
        user_id: str,
        policy_name: str = "api",
    ) -> Tuple[bool, int, int]:
        """
        API Rate Limit 확인
        
        Returns:
            (allowed, remaining, reset_after)
        """
        policy = self.POLICIES.get(policy_name, self.POLICIES["api"])
        key = f"{policy_name}:{user_id}"
        
        limiter = self._redis_limiter if self.use_redis else self._memory_limiter
        return await limiter.check_rate_limit(
            key,
            policy["max_attempts"],
            policy["window_seconds"],
        )
    
    async def record_api_request(
        self,
        user_id: str,
        policy_name: str = "api",
    ):
        """API 요청 기록"""
        key = f"{policy_name}:{user_id}"
        limiter = self._redis_limiter if self.use_redis else self._memory_limiter
        await limiter.record_attempt(key)


# 전역 인스턴스
rate_limit_service = RateLimitService(use_redis=True)
