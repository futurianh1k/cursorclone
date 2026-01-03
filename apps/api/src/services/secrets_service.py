"""
Secrets 관리 서비스

환경변수, HashiCorp Vault, Kubernetes Secrets 통합 관리

참조:
- HashiCorp Vault: https://www.vaultproject.io/
- hvac (Python Vault client): https://hvac.readthedocs.io/
- Kubernetes Secrets: https://kubernetes.io/docs/concepts/configuration/secret/
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


class SecretsProvider(ABC):
    """시크릿 제공자 추상 클래스"""
    
    @abstractmethod
    async def get_secret(self, key: str) -> Optional[str]:
        """시크릿 값 조회"""
        pass
    
    @abstractmethod
    async def set_secret(self, key: str, value: str) -> bool:
        """시크릿 값 설정"""
        pass
    
    @abstractmethod
    async def delete_secret(self, key: str) -> bool:
        """시크릿 삭제"""
        pass


class EnvironmentSecretsProvider(SecretsProvider):
    """
    환경변수 기반 시크릿 제공자
    
    개발 환경용 기본 제공자
    """
    
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
    
    async def get_secret(self, key: str) -> Optional[str]:
        full_key = f"{self.prefix}{key}" if self.prefix else key
        return os.getenv(full_key)
    
    async def set_secret(self, key: str, value: str) -> bool:
        full_key = f"{self.prefix}{key}" if self.prefix else key
        os.environ[full_key] = value
        return True
    
    async def delete_secret(self, key: str) -> bool:
        full_key = f"{self.prefix}{key}" if self.prefix else key
        if full_key in os.environ:
            del os.environ[full_key]
            return True
        return False


class VaultSecretsProvider(SecretsProvider):
    """
    HashiCorp Vault 기반 시크릿 제공자
    
    프로덕션 환경용
    
    설정:
        VAULT_ADDR: Vault 서버 주소 (예: https://vault.example.com:8200)
        VAULT_TOKEN: 인증 토큰
        VAULT_NAMESPACE: 네임스페이스 (선택)
        VAULT_MOUNT_POINT: KV 엔진 마운트 포인트 (기본: secret)
    """
    
    def __init__(
        self,
        addr: str = None,
        token: str = None,
        namespace: str = None,
        mount_point: str = "secret",
    ):
        self.addr = addr or os.getenv("VAULT_ADDR")
        self.token = token or os.getenv("VAULT_TOKEN")
        self.namespace = namespace or os.getenv("VAULT_NAMESPACE")
        self.mount_point = mount_point
        self._client = None
    
    def _get_client(self):
        """Vault 클라이언트 획득"""
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(
                    url=self.addr,
                    token=self.token,
                    namespace=self.namespace,
                )
                
                if not self._client.is_authenticated():
                    logger.error("Vault authentication failed")
                    self._client = None
            except ImportError:
                logger.error("hvac package not installed")
            except Exception as e:
                logger.error(f"Failed to connect to Vault: {e}")
        
        return self._client
    
    async def get_secret(self, key: str) -> Optional[str]:
        client = self._get_client()
        if not client:
            return None
        
        try:
            # KV v2 시크릿 읽기
            secret = client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point=self.mount_point,
            )
            return secret["data"]["data"].get("value")
        except Exception as e:
            logger.error(f"Failed to get secret {key}: {e}")
            return None
    
    async def set_secret(self, key: str, value: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.secrets.kv.v2.create_or_update_secret(
                path=key,
                secret={"value": value},
                mount_point=self.mount_point,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set secret {key}: {e}")
            return False
    
    async def delete_secret(self, key: str) -> bool:
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key,
                mount_point=self.mount_point,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {key}: {e}")
            return False


class KubernetesSecretsProvider(SecretsProvider):
    """
    Kubernetes Secrets 기반 시크릿 제공자
    
    Kubernetes 환경에서 마운트된 시크릿 파일 읽기
    
    시크릿은 /var/run/secrets/{namespace}/{secret-name}/{key} 경로에 마운트됨
    """
    
    def __init__(self, secrets_path: str = "/var/run/secrets"):
        self.secrets_path = Path(secrets_path)
    
    async def get_secret(self, key: str) -> Optional[str]:
        """
        시크릿 읽기
        
        key 형식: namespace/secret-name/key-name
        또는 간단히: secret-name/key-name (기본 네임스페이스)
        """
        secret_path = self.secrets_path / key
        
        if secret_path.exists():
            return secret_path.read_text().strip()
        
        # 환경변수에서 마운트된 시크릿 확인
        # Kubernetes는 시크릿을 환경변수로도 주입 가능
        env_key = key.replace("/", "_").upper()
        return os.getenv(env_key)
    
    async def set_secret(self, key: str, value: str) -> bool:
        """Kubernetes Secrets는 런타임에 수정 불가"""
        logger.warning("Kubernetes Secrets cannot be modified at runtime")
        return False
    
    async def delete_secret(self, key: str) -> bool:
        """Kubernetes Secrets는 런타임에 삭제 불가"""
        logger.warning("Kubernetes Secrets cannot be deleted at runtime")
        return False


class SecretsService:
    """
    통합 시크릿 서비스
    
    여러 제공자를 우선순위에 따라 시도
    """
    
    def __init__(self):
        self._providers: list[SecretsProvider] = []
        self._cache: Dict[str, str] = {}
        self._cache_ttl = 300  # 5분
        self._setup_providers()
    
    def _setup_providers(self):
        """제공자 설정 (우선순위 순서)"""
        secrets_provider = os.getenv("SECRETS_PROVIDER", "env")
        
        if secrets_provider == "vault":
            # Vault 우선
            vault_addr = os.getenv("VAULT_ADDR")
            if vault_addr:
                self._providers.append(VaultSecretsProvider())
                logger.info(f"Vault secrets provider configured: {vault_addr}")
        
        elif secrets_provider == "kubernetes":
            # Kubernetes Secrets
            if Path("/var/run/secrets/kubernetes.io").exists():
                self._providers.append(KubernetesSecretsProvider())
                logger.info("Kubernetes secrets provider configured")
        
        # 항상 환경변수를 폴백으로 추가
        self._providers.append(EnvironmentSecretsProvider())
        logger.info("Environment secrets provider configured (fallback)")
    
    async def get(self, key: str, default: str = None) -> Optional[str]:
        """
        시크릿 조회
        
        모든 제공자를 순서대로 시도
        """
        # 캐시 확인
        if key in self._cache:
            return self._cache[key]
        
        for provider in self._providers:
            try:
                value = await provider.get_secret(key)
                if value is not None:
                    self._cache[key] = value
                    return value
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
        
        return default
    
    async def get_required(self, key: str) -> str:
        """필수 시크릿 조회 (없으면 예외)"""
        value = await self.get(key)
        if value is None:
            raise ValueError(f"Required secret not found: {key}")
        return value
    
    async def set(self, key: str, value: str) -> bool:
        """시크릿 설정"""
        for provider in self._providers:
            try:
                if await provider.set_secret(key, value):
                    self._cache[key] = value
                    return True
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed to set: {e}")
        return False
    
    async def delete(self, key: str) -> bool:
        """시크릿 삭제"""
        success = False
        for provider in self._providers:
            try:
                if await provider.delete_secret(key):
                    success = True
            except Exception as e:
                logger.warning(f"Provider {provider.__class__.__name__} failed to delete: {e}")
        
        if key in self._cache:
            del self._cache[key]
        
        return success
    
    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()


# 싱글톤 인스턴스
secrets_service = SecretsService()


# ============================================================
# 편의 함수
# ============================================================

async def get_secret(key: str, default: str = None) -> Optional[str]:
    """시크릿 조회"""
    return await secrets_service.get(key, default)


async def get_database_url() -> str:
    """데이터베이스 URL 조회"""
    return await secrets_service.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/cursor_poc"
    )


async def get_redis_url() -> str:
    """Redis URL 조회"""
    return await secrets_service.get("REDIS_URL", "redis://localhost:6379/0")


async def get_jwt_secret() -> str:
    """JWT 시크릿 조회"""
    secret = await secrets_service.get("JWT_SECRET_KEY")
    if not secret:
        logger.warning("JWT_SECRET_KEY not set, using insecure default")
        return "insecure-default-key-change-in-production"
    return secret


async def get_encryption_key() -> str:
    """암호화 키 조회"""
    key = await secrets_service.get("MASTER_ENCRYPTION_KEY")
    if not key:
        logger.warning("MASTER_ENCRYPTION_KEY not set, using insecure default")
        return "insecure-default-key-change-in-production"
    return key
