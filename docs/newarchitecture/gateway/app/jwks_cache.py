import json
import time
import asyncio
from typing import Optional, Dict, Any
import urllib.request

from .config import settings

class JwksCache:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._jwks: Optional[Dict[str, Any]] = None
        self._loaded_at: float = 0.0
        self._last_refresh_attempt: float = 0.0
        self._stop = False

    async def start_background_refresh(self):
        if not settings.jwt_jwks_url:
            return
        while not self._stop:
            await asyncio.sleep(settings.jwt_jwks_refresh_seconds)
            try:
                await self.refresh(force=False)
            except Exception:
                # refresh errors handled in refresh()
                pass

    async def stop(self):
        self._stop = True

    def _expired(self) -> bool:
        if not self._jwks:
            return True
        return (time.time() - self._loaded_at) > settings.jwt_jwks_cache_ttl_seconds

    async def refresh(self, force: bool = False) -> Dict[str, Any]:
        async with self._lock:
            if not force and not self._expired():
                return self._jwks  # type: ignore
            if not settings.jwt_jwks_url:
                raise RuntimeError("JWKS_URL not set")

            self._last_refresh_attempt = time.time()
            try:
                with urllib.request.urlopen(settings.jwt_jwks_url, timeout=5) as r:
                    raw = r.read().decode("utf-8")
                jwks = json.loads(raw)
                self._jwks = jwks
                self._loaded_at = time.time()
                return jwks
            except Exception as e:
                # Fail-open vs fail-close:
                # - fail-open: keep using existing cached jwks if available (even if expired)
                # - fail-close: reject auth if cannot refresh and cache expired
                if settings.jwt_jwks_fail_open and self._jwks:
                    return self._jwks
                raise e

jwks_cache = JwksCache()
