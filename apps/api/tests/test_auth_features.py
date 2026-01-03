"""
인증 기능 테스트

- Rate Limiting
- Refresh Token
- 2FA (TOTP)
"""

import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from src.services.auth_service import (
    JWTAuthService,
    PasswordService,
)
from src.services.rate_limit_service import (
    InMemoryRateLimiter,
    RateLimitService,
)
from src.services.totp_service import (
    TOTPService,
    TwoFactorAuthService,
)


# ============================================================
# JWT 토큰 테스트
# ============================================================

class TestJWTAuthService:
    """JWT 서비스 테스트"""
    
    def test_create_access_token(self):
        """액세스 토큰 생성 테스트"""
        token = JWTAuthService.create_access_token("user123", "user@example.com", "developer")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """리프레시 토큰 생성 테스트"""
        token = JWTAuthService.create_refresh_token("user123", "user@example.com")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_token_pair(self):
        """토큰 쌍 생성 테스트"""
        tokens = JWTAuthService.create_token_pair("user123", "user@example.com", "admin")
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0
    
    def test_verify_access_token(self):
        """액세스 토큰 검증 테스트"""
        token = JWTAuthService.create_access_token("user123", "user@example.com")
        payload = JWTAuthService.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "user@example.com"
        assert payload["type"] == "access"
    
    def test_verify_refresh_token(self):
        """리프레시 토큰 검증 테스트"""
        token = JWTAuthService.create_refresh_token("user123", "user@example.com")
        payload = JWTAuthService.verify_refresh_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["type"] == "refresh"
        assert "jti" in payload
    
    def test_access_token_rejected_as_refresh(self):
        """액세스 토큰은 리프레시 토큰으로 사용 불가"""
        access_token = JWTAuthService.create_access_token("user123", "user@example.com")
        payload = JWTAuthService.verify_refresh_token(access_token)
        
        assert payload is None
    
    def test_refresh_token_rejected_as_access(self):
        """리프레시 토큰은 액세스 토큰으로 사용 불가"""
        refresh_token = JWTAuthService.create_refresh_token("user123", "user@example.com")
        payload = JWTAuthService.verify_token(refresh_token)
        
        assert payload is None
    
    def test_invalid_token_rejected(self):
        """유효하지 않은 토큰 거부"""
        payload = JWTAuthService.verify_token("invalid.token.here")
        assert payload is None
    
    def test_get_token_jti(self):
        """토큰 JTI 추출 테스트"""
        token = JWTAuthService.create_refresh_token("user123", "user@example.com")
        jti = JWTAuthService.get_token_jti(token)
        
        assert jti is not None
        assert len(jti) > 0


# ============================================================
# Rate Limiting 테스트
# ============================================================

class TestInMemoryRateLimiter:
    """인메모리 Rate Limiter 테스트"""
    
    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """제한 내 요청 허용"""
        limiter = InMemoryRateLimiter()
        
        allowed, remaining, _ = await limiter.check_rate_limit("test_key", 5, 60)
        assert allowed is True
        assert remaining == 5
    
    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        """제한 초과 요청 차단"""
        limiter = InMemoryRateLimiter()
        key = "test_key_over"
        
        # 5회 시도 기록
        for _ in range(5):
            await limiter.record_attempt(key)
        
        allowed, remaining, reset_after = await limiter.check_rate_limit(key, 5, 60)
        assert allowed is False
        assert remaining == 0
        assert reset_after > 0
    
    @pytest.mark.asyncio
    async def test_reset_clears_attempts(self):
        """리셋 후 시도 횟수 초기화"""
        limiter = InMemoryRateLimiter()
        key = "test_reset"
        
        # 시도 기록
        for _ in range(3):
            await limiter.record_attempt(key)
        
        # 리셋
        await limiter.reset(key)
        
        allowed, remaining, _ = await limiter.check_rate_limit(key, 5, 60)
        assert allowed is True
        assert remaining == 5


class TestRateLimitService:
    """Rate Limit 서비스 테스트"""
    
    @pytest.mark.asyncio
    async def test_login_rate_limit(self):
        """로그인 Rate Limit 테스트"""
        service = RateLimitService(use_redis=False)
        
        # 초기에는 허용
        allowed, msg = await service.check_login_rate_limit("user@example.com")
        assert allowed is True
        assert msg == ""
    
    @pytest.mark.asyncio
    async def test_login_rate_limit_blocks_after_failures(self):
        """실패 후 Rate Limit 차단"""
        service = RateLimitService(use_redis=False)
        email = "blocked_user@example.com"
        
        # 5회 실패 기록
        for _ in range(5):
            await service.record_login_attempt(email, success=False)
        
        allowed, msg = await service.check_login_rate_limit(email)
        assert allowed is False
        assert "Try again" in msg
    
    @pytest.mark.asyncio
    async def test_login_success_resets_limit(self):
        """로그인 성공 시 Rate Limit 리셋"""
        service = RateLimitService(use_redis=False)
        email = "reset_user@example.com"
        
        # 3회 실패 기록
        for _ in range(3):
            await service.record_login_attempt(email, success=False)
        
        # 성공 기록
        await service.record_login_attempt(email, success=True)
        
        # 리셋 확인
        allowed, _ = await service.check_login_rate_limit(email)
        assert allowed is True


# ============================================================
# TOTP 테스트
# ============================================================

class TestTOTPService:
    """TOTP 서비스 테스트"""
    
    def test_generate_secret(self):
        """시크릿 생성 테스트"""
        secret = TOTPService.generate_secret()
        
        assert secret is not None
        assert len(secret) > 0
        # Base32 문자만 포함
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in secret)
    
    def test_generate_totp(self):
        """TOTP 코드 생성 테스트"""
        secret = TOTPService.generate_secret()
        code = TOTPService.generate_totp(secret)
        
        assert code is not None
        assert len(code) == 6
        assert code.isdigit()
    
    def test_verify_totp_current(self):
        """현재 TOTP 코드 검증"""
        secret = TOTPService.generate_secret()
        code = TOTPService.generate_totp(secret)
        
        assert TOTPService.verify_totp(secret, code) is True
    
    def test_verify_totp_invalid(self):
        """유효하지 않은 TOTP 코드 거부"""
        secret = TOTPService.generate_secret()
        
        assert TOTPService.verify_totp(secret, "000000") is False
        assert TOTPService.verify_totp(secret, "123456") is False
    
    def test_verify_totp_with_window(self):
        """윈도우 내 TOTP 코드 허용"""
        secret = TOTPService.generate_secret()
        
        # 30초 전 코드
        past_time = int(time.time()) - 30
        past_code = TOTPService.generate_totp(secret, past_time)
        
        # 윈도우 1 (±30초) 내에서 허용
        assert TOTPService.verify_totp(secret, past_code, window=1) is True
    
    def test_provisioning_uri(self):
        """프로비저닝 URI 생성 테스트"""
        secret = "JBSWY3DPEHPK3PXP"
        uri = TOTPService.get_provisioning_uri(secret, "user@example.com", "TestApp")
        
        assert uri.startswith("otpauth://totp/")
        assert "secret=" in uri
        assert "issuer=" in uri
        assert "algorithm=" in uri
    
    def test_generate_backup_codes(self):
        """백업 코드 생성 테스트"""
        codes = TOTPService.generate_backup_codes(10)
        
        assert len(codes) == 10
        for code, hash in codes:
            assert len(code) == 8  # 8자리 hex
            assert len(hash) == 64  # SHA-256 해시
    
    def test_verify_backup_code(self):
        """백업 코드 검증 테스트"""
        codes = TOTPService.generate_backup_codes(1)
        code, hash = codes[0]
        
        assert TOTPService.verify_backup_code(code, hash) is True
        assert TOTPService.verify_backup_code("WRONG123", hash) is False


class TestTwoFactorAuthService:
    """2FA 서비스 테스트"""
    
    def test_setup_2fa(self):
        """2FA 설정 테스트"""
        service = TwoFactorAuthService()
        setup_data = service.setup_2fa("user123", "user@example.com")
        
        assert "secret" in setup_data
        assert "secret_plain" in setup_data
        assert "provisioning_uri" in setup_data
        assert "backup_codes" in setup_data
        assert len(setup_data["backup_codes"]) == 10
    
    def test_verify_2fa_setup(self):
        """2FA 설정 검증 테스트"""
        service = TwoFactorAuthService()
        setup_data = service.setup_2fa("user123", "user@example.com")
        
        # 현재 코드 생성
        code = TOTPService.generate_totp(setup_data["secret_plain"])
        
        # 검증
        assert service.verify_2fa_setup(setup_data["secret_plain"], code, is_encrypted=False) is True
    
    def test_verify_2fa_login_with_totp(self):
        """TOTP로 2FA 로그인 검증"""
        service = TwoFactorAuthService()
        setup_data = service.setup_2fa("user123", "user@example.com")
        secret = setup_data["secret_plain"]
        code = TOTPService.generate_totp(secret)
        
        verified, used_backup = service.verify_2fa_login(secret, code, is_encrypted=False)
        
        assert verified is True
        assert used_backup is None
    
    def test_verify_2fa_login_with_backup_code(self):
        """백업 코드로 2FA 로그인 검증"""
        service = TwoFactorAuthService()
        setup_data = service.setup_2fa("user123", "user@example.com")
        secret = setup_data["secret_plain"]
        
        backup_code, backup_hash = setup_data["backup_codes"][0]
        backup_hashes = [h for _, h in setup_data["backup_codes"]]
        
        verified, used_backup = service.verify_2fa_login(
            secret, 
            backup_code, 
            backup_hashes,
            is_encrypted=False,
        )
        
        assert verified is True
        assert used_backup == backup_hash


# ============================================================
# 비밀번호 서비스 테스트
# ============================================================

class TestPasswordService:
    """비밀번호 서비스 테스트"""
    
    def test_hash_password(self):
        """비밀번호 해싱 테스트"""
        password = "SecurePassword123!"
        hash = PasswordService.hash_password(password)
        
        assert hash is not None
        assert hash != password
        assert hash.startswith("$2")  # bcrypt prefix
    
    def test_verify_correct_password(self):
        """올바른 비밀번호 검증"""
        password = "SecurePassword123!"
        hash = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password(password, hash) is True
    
    def test_verify_wrong_password(self):
        """잘못된 비밀번호 거부"""
        password = "SecurePassword123!"
        hash = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password("WrongPassword", hash) is False
    
    def test_different_hashes_for_same_password(self):
        """같은 비밀번호도 다른 해시 생성 (salt)"""
        password = "SamePassword!"
        hash1 = PasswordService.hash_password(password)
        hash2 = PasswordService.hash_password(password)
        
        assert hash1 != hash2  # 다른 salt 사용
        assert PasswordService.verify_password(password, hash1) is True
        assert PasswordService.verify_password(password, hash2) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
