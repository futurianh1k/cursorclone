"""
TOTP (Time-based One-Time Password) 서비스

2FA (Two-Factor Authentication) 구현

참조:
- RFC 6238: TOTP Algorithm
- Google Authenticator, Authy 호환
"""

import os
import base64
import secrets
import hashlib
import hmac
import struct
import time
import logging
from typing import Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class TOTPService:
    """
    TOTP 서비스
    
    Google Authenticator, Microsoft Authenticator, Authy 등과 호환
    """
    
    # 설정
    ISSUER = os.getenv("TOTP_ISSUER", "Cursor On-Prem")
    DIGITS = 6              # OTP 자릿수
    PERIOD = 30             # 유효 기간 (초)
    ALGORITHM = "SHA1"      # HMAC 알고리즘
    SECRET_LENGTH = 20      # 시크릿 길이 (bytes)
    BACKUP_CODES_COUNT = 10 # 백업 코드 개수
    
    @staticmethod
    def generate_secret() -> str:
        """
        TOTP 시크릿 생성
        
        Returns:
            Base32 인코딩된 시크릿 (저장용)
        """
        # 160비트 (20바이트) 랜덤 시크릿
        secret_bytes = secrets.token_bytes(TOTPService.SECRET_LENGTH)
        # Base32 인코딩 (RFC 4648)
        return base64.b32encode(secret_bytes).decode().rstrip("=")
    
    @staticmethod
    def get_provisioning_uri(
        secret: str,
        email: str,
        issuer: Optional[str] = None,
    ) -> str:
        """
        QR 코드용 프로비저닝 URI 생성
        
        형식: otpauth://totp/{issuer}:{account}?secret={secret}&issuer={issuer}&algorithm={algo}&digits={digits}&period={period}
        
        Args:
            secret: Base32 시크릿
            email: 사용자 이메일 (계정명으로 사용)
            issuer: 발급자 이름
        
        Returns:
            otpauth:// URI
        """
        issuer = issuer or TOTPService.ISSUER
        # URL 인코딩
        from urllib.parse import quote
        
        params = {
            "secret": secret,
            "issuer": issuer,
            "algorithm": TOTPService.ALGORITHM,
            "digits": str(TOTPService.DIGITS),
            "period": str(TOTPService.PERIOD),
        }
        
        param_str = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        label = f"{quote(issuer)}:{quote(email)}"
        
        return f"otpauth://totp/{label}?{param_str}"
    
    @staticmethod
    def generate_totp(secret: str, timestamp: Optional[int] = None) -> str:
        """
        TOTP 코드 생성
        
        Args:
            secret: Base32 시크릿
            timestamp: Unix 타임스탬프 (테스트용)
        
        Returns:
            6자리 OTP 코드
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # 타임 스텝 계산
        time_step = timestamp // TOTPService.PERIOD
        
        # 시크릿 디코딩
        secret_bytes = TOTPService._decode_secret(secret)
        
        # HMAC-SHA1 계산
        time_bytes = struct.pack(">Q", time_step)
        hmac_hash = hmac.new(secret_bytes, time_bytes, hashlib.sha1).digest()
        
        # Dynamic Truncation
        offset = hmac_hash[-1] & 0x0F
        code_int = struct.unpack(">I", hmac_hash[offset:offset+4])[0]
        code_int = code_int & 0x7FFFFFFF  # 최상위 비트 제거
        code_int = code_int % (10 ** TOTPService.DIGITS)
        
        # 자릿수 맞추기
        return str(code_int).zfill(TOTPService.DIGITS)
    
    @staticmethod
    def verify_totp(
        secret: str,
        code: str,
        window: int = 1,
    ) -> bool:
        """
        TOTP 코드 검증
        
        Args:
            secret: Base32 시크릿
            code: 사용자 입력 코드
            window: 허용 윈도우 (앞뒤 N개 타임스텝)
        
        Returns:
            검증 성공 여부
        """
        if not code or len(code) != TOTPService.DIGITS:
            return False
        
        current_time = int(time.time())
        
        # 현재 ± window 범위 확인
        for offset in range(-window, window + 1):
            timestamp = current_time + (offset * TOTPService.PERIOD)
            expected = TOTPService.generate_totp(secret, timestamp)
            if secrets.compare_digest(expected, code):
                return True
        
        return False
    
    @staticmethod
    def generate_backup_codes(count: Optional[int] = None) -> list:
        """
        백업 코드 생성
        
        2FA 설정 시 백업 코드를 생성하여 사용자에게 제공
        각 코드는 1회만 사용 가능
        
        Returns:
            [(code, code_hash), ...] 리스트
        """
        count = count or TOTPService.BACKUP_CODES_COUNT
        codes = []
        
        for _ in range(count):
            # 8자리 숫자+문자 코드 (읽기 쉬운 형식)
            code = secrets.token_hex(4).upper()  # 8자리 16진수
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            codes.append((code, code_hash))
        
        return codes
    
    @staticmethod
    def verify_backup_code(code: str, code_hash: str) -> bool:
        """백업 코드 검증"""
        computed_hash = hashlib.sha256(code.upper().encode()).hexdigest()
        return secrets.compare_digest(computed_hash, code_hash)
    
    @staticmethod
    def _decode_secret(secret: str) -> bytes:
        """Base32 시크릿 디코딩"""
        # 패딩 추가
        padding = (8 - len(secret) % 8) % 8
        secret_padded = secret + "=" * padding
        return base64.b32decode(secret_padded.upper())


class TwoFactorAuthService:
    """
    2FA 관리 서비스
    
    사용자별 2FA 설정, 검증, 백업 코드 관리
    """
    
    def __init__(self, encryption_service=None):
        """
        Args:
            encryption_service: 시크릿 암호화용 서비스
        """
        self.encryption = encryption_service
        self.totp = TOTPService()
    
    def setup_2fa(self, user_id: str, email: str) -> dict:
        """
        2FA 설정 시작
        
        Returns:
            {
                "secret": str (암호화됨),
                "secret_plain": str (QR 코드용, 1회만 표시),
                "provisioning_uri": str,
                "backup_codes": [(code, hash), ...],
            }
        """
        # 시크릿 생성
        secret = TOTPService.generate_secret()
        
        # 프로비저닝 URI
        uri = TOTPService.get_provisioning_uri(secret, email)
        
        # 백업 코드 생성
        backup_codes = TOTPService.generate_backup_codes()
        
        # 시크릿 암호화 (저장용)
        encrypted_secret = secret
        if self.encryption:
            encrypted_secret = self.encryption.encrypt(secret)
        
        logger.info(f"2FA setup initiated for user {user_id}")
        
        return {
            "secret": encrypted_secret,
            "secret_plain": secret,  # 1회만 표시
            "provisioning_uri": uri,
            "backup_codes": backup_codes,
        }
    
    def verify_2fa_setup(
        self,
        secret: str,
        code: str,
        is_encrypted: bool = True,
    ) -> bool:
        """
        2FA 설정 완료 검증
        
        사용자가 입력한 코드가 올바른지 확인
        """
        # 시크릿 복호화
        decrypted_secret = secret
        if is_encrypted and self.encryption:
            try:
                decrypted_secret = self.encryption.decrypt(secret)
            except Exception as e:
                logger.error(f"Failed to decrypt 2FA secret: {e}")
                return False
        
        return TOTPService.verify_totp(decrypted_secret, code)
    
    def verify_2fa_login(
        self,
        secret: str,
        code: str,
        backup_code_hashes: Optional[list] = None,
        is_encrypted: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        2FA 로그인 검증
        
        TOTP 코드 또는 백업 코드로 검증
        
        Args:
            secret: 암호화된 시크릿
            code: 사용자 입력 코드
            backup_code_hashes: 백업 코드 해시 목록
            is_encrypted: 시크릿 암호화 여부
        
        Returns:
            (verified, used_backup_code_hash)
            - verified: 검증 성공 여부
            - used_backup_code_hash: 사용된 백업 코드 해시 (TOTP면 None)
        """
        # 시크릿 복호화
        decrypted_secret = secret
        if is_encrypted and self.encryption:
            try:
                decrypted_secret = self.encryption.decrypt(secret)
            except Exception:
                return False, None
        
        # TOTP 코드 검증
        if TOTPService.verify_totp(decrypted_secret, code):
            return True, None
        
        # 백업 코드 검증
        if backup_code_hashes:
            for code_hash in backup_code_hashes:
                if TOTPService.verify_backup_code(code, code_hash):
                    return True, code_hash
        
        return False, None


# 전역 인스턴스 (암호화 서비스 주입 필요)
def get_2fa_service():
    """2FA 서비스 인스턴스 가져오기"""
    from .auth_service import encryption_service
    return TwoFactorAuthService(encryption_service)
