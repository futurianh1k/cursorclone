"""
인증 서비스
SSH 키, mTLS, API 키 기반 인증 관리
상용 SaaS 수준의 보안 구현
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
import bcrypt
from jose import JWTError, jwt
import base64 as _b64

# JWT 설정
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_ACCESS_EXPIRATION_MINUTES = 15  # 액세스 토큰: 15분
JWT_REFRESH_EXPIRATION_DAYS = 7    # 리프레시 토큰: 7일

# Gateway(JWKS/RS256) 설정 (newarchitecture v0.3)
GATEWAY_JWT_ALGORITHM = "RS256"
GATEWAY_TOKEN_TTL_MINUTES = int(os.getenv("GATEWAY_TOKEN_TTL_MINUTES", "720"))  # 12h
GATEWAY_JWT_KEY_ID = os.getenv("GATEWAY_JWT_KEY_ID", "gateway-key-1")
GATEWAY_JWT_PRIVATE_KEY_PEM = os.getenv("GATEWAY_JWT_PRIVATE_KEY_PEM")  # PEM string
GATEWAY_JWT_KEY_DIR = os.getenv("GATEWAY_JWT_KEY_DIR", "/tmp/cursor-poc-keys")
GATEWAY_JWT_PRIVATE_KEY_FILE = os.getenv("GATEWAY_JWT_PRIVATE_KEY_FILE", os.path.join(GATEWAY_JWT_KEY_DIR, "gateway_jwt_private.pem"))


def _b64url_uint(n: int) -> str:
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return _b64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


class GatewayJWKSService:
    """
    Gateway 토큰 발급 및 JWKS 제공 (RS256)
    - 금융권 VDE: 외부 IdP 없이 내부 구성도 가능하나, 운영에서는 키를 Secret으로 주입 권장
    """

    def __init__(self):
        self._kid = GATEWAY_JWT_KEY_ID
        self._private_key_pem, self._public_jwk = self._load_or_generate_keys()

    def _load_or_generate_keys(self) -> tuple[str, dict]:
        # 운영: PEM 환경변수 주입 권장
        if GATEWAY_JWT_PRIVATE_KEY_PEM and "BEGIN" in GATEWAY_JWT_PRIVATE_KEY_PEM:
            private_pem = GATEWAY_JWT_PRIVATE_KEY_PEM
            private_key = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
            public_key = private_key.public_key()
        else:
            # 개발/PoC: 컨테이너 파일로 키를 고정 (프로세스/재시작 간 일관성)
            os.makedirs(GATEWAY_JWT_KEY_DIR, exist_ok=True)
            if os.path.exists(GATEWAY_JWT_PRIVATE_KEY_FILE):
                private_pem = open(GATEWAY_JWT_PRIVATE_KEY_FILE, "r", encoding="utf-8").read()
                private_key = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
                public_key = private_key.public_key()
            else:
                private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                public_key = private_key.public_key()
                private_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ).decode("utf-8")
                # 파일 저장(권한 최소화)
                tmp = GATEWAY_JWT_PRIVATE_KEY_FILE + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(private_pem)
                os.replace(tmp, GATEWAY_JWT_PRIVATE_KEY_FILE)
                try:
                    os.chmod(GATEWAY_JWT_PRIVATE_KEY_FILE, 0o600)
                except Exception:
                    pass

        pub_numbers = public_key.public_numbers()
        jwk = {
            "kty": "RSA",
            "use": "sig",
            "kid": self._kid,
            "alg": GATEWAY_JWT_ALGORITHM,
            "n": _b64url_uint(pub_numbers.n),
            "e": _b64url_uint(pub_numbers.e),
        }
        return private_pem, jwk

    def jwks(self) -> dict:
        return {"keys": [self._public_jwk]}

    def create_gateway_token(
        self,
        user_id: str,
        tenant_id: str,
        project_id: str,
        workspace_id: str,
        role: str,
    ) -> str:
        expires_at = datetime.utcnow() + timedelta(minutes=GATEWAY_TOKEN_TTL_MINUTES)
        payload = {
            "sub": user_id,
            # v0.3 기대 클레임 키 (gateway/app/auth_async.py와 정합)
            "tid": tenant_id,
            "pid": project_id,
            "wid": workspace_id,
            "role": role,
            "type": "gateway",
            "exp": expires_at,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self._private_key_pem, algorithm=GATEWAY_JWT_ALGORITHM, headers={"kid": self._kid})


class EncryptionService:
    """암호화 서비스 (Fernet 기반)"""
    
    def __init__(self, key: Optional[bytes] = None):
        """
        암호화 서비스 초기화
        
        Args:
            key: 마스터 암호화 키 (없으면 환경변수에서 로드)
        """
        if key is None:
            key_str = os.getenv("MASTER_ENCRYPTION_KEY")
            if not key_str:
                # 개발 환경: 자동 생성 (프로덕션에서는 반드시 설정 필요)
                import warnings
                warnings.warn(
                    "MASTER_ENCRYPTION_KEY not set. Using auto-generated key (NOT SECURE FOR PRODUCTION)",
                    UserWarning
                )
                key = Fernet.generate_key()
            else:
                # 환경변수에서 가져온 키를 bytes로 변환
                try:
                    # 이미 base64 인코딩된 키인지 확인
                    key = key_str.encode() if isinstance(key_str, str) else key_str
                    # Fernet 키 형식 검증을 위해 임시로 Fernet 객체 생성 시도
                    Fernet(key)
                except ValueError:
                    # 유효하지 않은 키인 경우 새로 생성
                    import warnings
                    warnings.warn(
                        f"Invalid MASTER_ENCRYPTION_KEY format. Generating new key.",
                        UserWarning
                    )
                    key = Fernet.generate_key()
        
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """텍스트 암호화"""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """텍스트 복호화"""
        return self.cipher.decrypt(ciphertext.encode()).decode()


class PasswordService:
    """비밀번호 해싱 서비스"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """비밀번호 해싱 (bcrypt)"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """비밀번호 검증"""
        return bcrypt.checkpw(password.encode(), password_hash.encode())


class JWTAuthService:
    """
    JWT 토큰 서비스
    
    토큰 유형:
    - Access Token: 짧은 수명 (15분), API 접근용
    - Refresh Token: 긴 수명 (7일), 토큰 갱신용
    """
    
    @staticmethod
    def create_access_token(user_id: str, email: str, role: str = "developer") -> str:
        """
        JWT 액세스 토큰 생성 (15분)
        
        Args:
            user_id: 사용자 ID
            email: 이메일
            role: 역할 (권한 체크용)
        """
        expires_at = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_EXPIRATION_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": expires_at,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(user_id: str, email: str) -> str:
        """
        JWT 리프레시 토큰 생성 (7일)
        
        리프레시 토큰은 액세스 토큰 갱신에만 사용됩니다.
        """
        expires_at = datetime.utcnow() + timedelta(days=JWT_REFRESH_EXPIRATION_DAYS)
        token_id = secrets.token_urlsafe(16)  # 토큰 고유 ID (폐기용)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "jti": token_id,  # JWT ID (토큰 폐기용)
            "exp": expires_at,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, JWT_REFRESH_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def create_token_pair(user_id: str, email: str, role: str = "developer") -> dict:
        """
        액세스/리프레시 토큰 쌍 생성
        
        Returns:
            {
                "access_token": str,
                "refresh_token": str,
                "token_type": "bearer",
                "expires_in": int (초)
            }
        """
        access_token = JWTAuthService.create_access_token(user_id, email, role)
        refresh_token = JWTAuthService.create_refresh_token(user_id, email)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": JWT_ACCESS_EXPIRATION_MINUTES * 60,
        }
    
    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """JWT 액세스 토큰 검증"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            # 액세스 토큰인지 확인
            if payload.get("type") != "access":
                # 이전 버전 토큰 (type 없음)도 허용
                if "type" in payload:
                    return None
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def verify_refresh_token(token: str) -> Optional[dict]:
        """JWT 리프레시 토큰 검증"""
        try:
            payload = jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            # 리프레시 토큰인지 확인
            if payload.get("type") != "refresh":
                return None
            return payload
        except JWTError:
            return None
    
    @staticmethod
    def get_token_jti(token: str) -> Optional[str]:
        """리프레시 토큰의 JTI (토큰 ID) 추출"""
        payload = JWTAuthService.verify_refresh_token(token)
        if payload:
            return payload.get("jti")
        return None

    # ============================================================
    # Gateway v0.3 (JWKS/RS256) helpers
    # ============================================================

    @staticmethod
    def get_gateway_jwks() -> dict:
        return gateway_jwks_service.jwks()

    @staticmethod
    def create_gateway_workspace_token(
        user_id: str,
        tenant_id: str,
        project_id: str,
        workspace_id: str,
        role: str,
    ) -> str:
        return gateway_jwks_service.create_gateway_token(
            user_id=user_id,
            tenant_id=tenant_id,
            project_id=project_id,
            workspace_id=workspace_id,
            role=role,
        )


class SSHAuthService:
    """SSH 키 기반 인증 서비스"""
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service
    
    def encrypt_private_key(self, private_key: str) -> str:
        """SSH 비공개키 암호화"""
        return self.encryption.encrypt(private_key)
    
    def decrypt_private_key(self, encrypted_key: str) -> str:
        """SSH 비공개키 복호화"""
        return self.encryption.decrypt(encrypted_key)
    
    def get_key_fingerprint(self, public_key: str) -> str:
        """
        SSH 공개키 지문 생성 (SHA-256)
        
        Args:
            public_key: SSH 공개키 문자열 (예: "ssh-rsa AAAAB3NzaC1yc2E...")
        
        Returns:
            SHA-256 해시 (hex)
        """
        # SSH 공개키 형식: "ssh-rsa AAAAB3NzaC1yc2E... comment"
        parts = public_key.strip().split()
        if len(parts) < 2:
            raise ValueError("Invalid SSH public key format")
        
        # Base64 인코딩된 키 부분 추출
        key_part = parts[1]
        try:
            key_bytes = base64.b64decode(key_part)
            return hashlib.sha256(key_bytes).hexdigest()
        except Exception as e:
            raise ValueError(f"Failed to decode SSH public key: {e}")
    
    def generate_ssh_key_pair(self) -> Tuple[str, str]:
        """
        SSH 키 쌍 생성
        
        Returns:
            (private_key, public_key) 튜플
        """
        # RSA 키 생성
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # 비공개키를 PEM 형식으로 변환
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        
        # 공개키 추출
        public_key_obj = private_key.public_key()
        public_ssh = public_key_obj.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        ).decode()
        
        # SSH 형식으로 변환
        public_key = f"ssh-rsa {base64.b64encode(public_ssh.encode()).decode()}"
        
        return private_pem, public_key


class mTLSAuthService:
    """mTLS 인증 서비스"""
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service
    
    def encrypt_certificate(self, cert: str, key: str) -> Tuple[str, str]:
        """인증서 및 키 암호화"""
        encrypted_cert = self.encryption.encrypt(cert)
        encrypted_key = self.encryption.encrypt(key)
        return encrypted_cert, encrypted_key
    
    def decrypt_certificate(self, encrypted_cert: str, encrypted_key: str) -> Tuple[str, str]:
        """인증서 및 키 복호화"""
        cert = self.encryption.decrypt(encrypted_cert)
        key = self.encryption.decrypt(encrypted_key)
        return cert, key
    
    def validate_certificate(self, cert_pem: str) -> dict:
        """
        인증서 유효성 검증
        
        Returns:
            {
                "valid": bool,
                "expires_at": datetime,
                "subject": str,
                "issuer": str,
            }
        """
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode())
            
            # 만료일 확인
            expires_at = cert.not_valid_after
            
            # 주체 정보
            subject = cert.subject.rfc4514_string()
            issuer = cert.issuer.rfc4514_string()
            
            return {
                "valid": datetime.utcnow() < expires_at,
                "expires_at": expires_at.isoformat(),
                "subject": subject,
                "issuer": issuer,
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }


class APIKeyAuthService:
    """API 키 인증 서비스"""
    
    @staticmethod
    def generate_api_key() -> Tuple[str, str]:
        """
        API 키 생성
        
        Returns:
            (key, key_hash) 튜플
            - key: 평문 API 키 (한 번만 표시)
            - key_hash: 저장용 해시
        """
        # URL-safe 랜덤 키 생성 (32바이트 = 256비트)
        key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, key_hash
    
    @staticmethod
    def verify_api_key(key: str, key_hash: str) -> bool:
        """API 키 검증"""
        computed_hash = hashlib.sha256(key.encode()).hexdigest()
        return secrets.compare_digest(computed_hash, key_hash)
    
    @staticmethod
    def rotate_api_key(old_key_hash: Optional[str] = None) -> Tuple[str, str]:
        """
        API 키 회전
        
        Args:
            old_key_hash: 이전 키 해시 (무효화용, 선택사항)
        
        Returns:
            (new_key, new_key_hash) 튜플
        """
        return APIKeyAuthService.generate_api_key()


# 전역 인스턴스
encryption_service = EncryptionService()
password_service = PasswordService()
jwt_auth_service = JWTAuthService()
gateway_jwks_service = GatewayJWKSService()
ssh_auth_service = SSHAuthService(encryption_service)
mtls_auth_service = mTLSAuthService(encryption_service)
api_key_auth_service = APIKeyAuthService()
