"""
Auth 라우터
- POST /api/auth/signup (회원가입)
- POST /api/auth/login (로그인)
- POST /api/auth/logout (로그아웃)
- POST /api/auth/refresh (토큰 갱신)
- GET /api/auth/me (현재 사용자 정보)
- POST /api/auth/2fa/setup (2FA 설정)
- POST /api/auth/2fa/verify (2FA 검증)
- POST /api/auth/2fa/disable (2FA 비활성화)

기능:
- JWT Access/Refresh Token
- Rate Limiting (로그인 시도 제한)
- 2FA (TOTP 기반)
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import secrets
import logging

from ..middleware.rate_limiter import limiter

from ..models import (
    SignUpRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
    ErrorResponse,
)
from ..db import get_db, UserModel, OrganizationModel, UserSessionModel
from ..services.auth_service import (
    password_service,
    jwt_auth_service,
)
from ..services.rate_limit_service import rate_limit_service
from ..services.totp_service import get_2fa_service, TOTPService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


# ============================================================
# 추가 요청/응답 모델
# ============================================================

class RefreshTokenRequest(BaseModel):
    """토큰 갱신 요청"""
    refresh_token: str = Field(..., description="리프레시 토큰")


class RefreshTokenResponse(BaseModel):
    """토큰 갱신 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="액세스 토큰 만료 시간 (초)")


class Setup2FAResponse(BaseModel):
    """2FA 설정 응답"""
    secret: str = Field(..., description="암호화된 시크릿 (확인용)")
    provisioning_uri: str = Field(..., description="QR 코드용 URI")
    backup_codes: list = Field(..., description="백업 코드 목록")


class Verify2FARequest(BaseModel):
    """2FA 검증 요청"""
    code: str = Field(..., min_length=6, max_length=8, description="TOTP 코드 또는 백업 코드")


class LoginWith2FARequest(LoginRequest):
    """2FA 포함 로그인 요청"""
    totp_code: Optional[str] = Field(None, description="TOTP 코드 (2FA 활성화 시 필수)")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserModel:
    """
    현재 인증된 사용자 가져오기 (의존성)
    
    JWT 토큰 또는 세션 토큰으로 인증
    """
    token = credentials.credentials
    
    # JWT 토큰 검증
    payload = jwt_auth_service.verify_token(token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            user = await db.execute(
                select(UserModel).where(UserModel.user_id == user_id)
            )
            user = user.scalar_one_or_none()
            if user:
                return user
    
    # 세션 토큰 검증 (대체 방법)
    session = await db.execute(
        select(UserSessionModel).where(
            UserSessionModel.session_token == token,
            UserSessionModel.expires_at > datetime.utcnow(),
        )
    )
    session = session.scalar_one_or_none()
    if session:
        user = await db.get(UserModel, session.user_id)
        if user:
            return user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "Invalid or expired token", "code": "UNAUTHORIZED"},
    )


@router.post(
    "/signup",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        409: {"model": ErrorResponse, "description": "User already exists"},
    },
    summary="회원가입",
    description="새 사용자를 등록합니다.",
)
async def signup(
    request: SignUpRequest,
    db: AsyncSession = Depends(get_db),
):
    """회원가입"""
    # 이메일 중복 확인
    existing = await db.execute(
        select(UserModel).where(UserModel.email == request.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "User already exists", "code": "USER_EXISTS"},
        )
    
    # 조직 생성 또는 조회
    org_id = f"org_{request.org_name.lower().replace(' ', '-')}" if request.org_name else "org_default"
    
    org = await db.execute(
        select(OrganizationModel).where(OrganizationModel.org_id == org_id)
    )
    org = org.scalar_one_or_none()
    
    if not org:
        org = OrganizationModel(
            org_id=org_id,
            name=request.org_name or "Default Organization",
        )
        db.add(org)
        await db.flush()
    
    # 사용자 생성
    user_id = f"u_{secrets.token_urlsafe(8)}"
    password_hash = password_service.hash_password(login_request.password)
    
    user = UserModel(
        user_id=user_id,
        email=request.email,
        name=request.name,
        password_hash=password_hash,
        org_id=org.org_id,
        role="developer",
    )
    db.add(user)
    await db.flush()
    
    # JWT 토큰 생성
    access_token = jwt_auth_service.create_access_token(user_id, request.email)
    
    # 세션 생성 (선택사항)
    session_token = secrets.token_urlsafe(32)
    session = UserSessionModel(
        user_id=user.user_id,
        session_token=session_token,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    db.add(session)
    
    await db.commit()
    
    return LoginResponse(
        accessToken=access_token,
        tokenType="bearer",
        user=UserResponse(
            userId=user.user_id,
            email=user.email,
            name=user.name,
            orgId=user.org_id,
            role=user.role,
            avatarUrl=user.avatar_url,
        ),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        429: {"model": ErrorResponse, "description": "Too many attempts"},
    },
    summary="로그인",
    description="사용자 로그인 (Rate Limiting, 2FA 지원)",
)
async def login(
    request: Request,
    login_request: LoginWith2FARequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    로그인
    
    - Rate Limiting: 5분에 5회 시도 제한
    - 2FA: 활성화된 경우 TOTP 코드 필수
    - Refresh Token: 응답에 포함
    """
    ip_address = request.client.host
    
    # Rate Limit 확인
    allowed, rate_limit_msg = await rate_limit_service.check_login_rate_limit(
        login_request.email.lower(),
        ip_address,
    )
    if not allowed:
        logger.warning(f"Login rate limit exceeded: {login_request.email} from {ip_address}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": rate_limit_msg, "code": "RATE_LIMITED"},
        )
    
    # 사용자 조회
    user = await db.execute(
        select(UserModel).where(UserModel.email == login_request.email.lower())
    )
    user = user.scalar_one_or_none()
    
    if not user:
        # 실패 기록
        await rate_limit_service.record_login_attempt(login_request.email.lower(), ip_address, success=False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid email or password", "code": "INVALID_CREDENTIALS"},
        )
    
    # 비밀번호 검증
    if user.password_hash:
        if not password_service.verify_password(login_request.password, user.password_hash):
            await rate_limit_service.record_login_attempt(login_request.email.lower(), ip_address, success=False)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid email or password", "code": "INVALID_CREDENTIALS"},
            )
    
    # 2FA 검증 (활성화된 경우)
    # 참고: UserModel에 totp_secret, totp_enabled 필드 필요
    if hasattr(user, 'totp_enabled') and user.totp_enabled:
        if not login_request.totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "2FA code required", "code": "2FA_REQUIRED"},
            )
        
        # 2FA 검증
        two_fa_service = get_2fa_service()
        verified, used_backup = two_fa_service.verify_2fa_login(
            user.totp_secret,
            login_request.totp_code,
            user.backup_code_hashes if hasattr(user, 'backup_code_hashes') else None,
        )
        
        if not verified:
            await rate_limit_service.record_login_attempt(login_request.email.lower(), ip_address, success=False)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid 2FA code", "code": "INVALID_2FA"},
            )
        
        # 백업 코드 사용 시 제거
        if used_backup and hasattr(user, 'backup_code_hashes'):
            user.backup_code_hashes = [h for h in user.backup_code_hashes if h != used_backup]
    
    # 로그인 성공
    await rate_limit_service.record_login_attempt(login_request.email.lower(), ip_address, success=True)
    
    # 마지막 로그인 시간 업데이트
    user.last_login_at = datetime.utcnow()
    
    # JWT 토큰 쌍 생성 (Access + Refresh)
    tokens = jwt_auth_service.create_token_pair(user.user_id, user.email, user.role)
    
    # 세션 생성 (리프레시 토큰 저장용)
    user_agent = request.headers.get("user-agent") if request else None
    
    session = UserSessionModel(
        user_id=user.user_id,
        session_token=tokens["refresh_token"][:255],  # 토큰 일부만 저장 (인덱싱용)
        expires_at=datetime.utcnow() + timedelta(days=7),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    
    await db.commit()
    
    logger.info(f"User logged in: {user.user_id} from {ip_address}")
    
    return LoginResponse(
        accessToken=tokens["access_token"],
        refreshToken=tokens["refresh_token"],
        tokenType="bearer",
        expiresIn=tokens["expires_in"],
        user=UserResponse(
            userId=user.user_id,
            email=user.email,
            name=user.name,
            orgId=user.org_id,
            role=user.role,
            avatarUrl=user.avatar_url,
        ),
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
    },
    summary="토큰 갱신",
    description="리프레시 토큰으로 새 액세스 토큰 발급",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    토큰 갱신
    
    리프레시 토큰을 사용하여 새 액세스/리프레시 토큰 쌍 발급
    """
    # 리프레시 토큰 검증
    payload = jwt_auth_service.verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid or expired refresh token", "code": "INVALID_REFRESH_TOKEN"},
        )
    
    user_id = payload.get("sub")
    email = payload.get("email")
    
    # 사용자 조회
    user = await db.execute(
        select(UserModel).where(UserModel.user_id == user_id)
    )
    user = user.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "User not found", "code": "USER_NOT_FOUND"},
        )
    
    # 새 토큰 쌍 생성
    tokens = jwt_auth_service.create_token_pair(user.user_id, user.email, user.role)
    
    logger.info(f"Token refreshed for user: {user_id}")
    
    return RefreshTokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=tokens["expires_in"],
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="로그아웃",
    description="사용자 로그아웃",
)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """로그아웃"""
    token = credentials.credentials
    
    # 세션 삭제
    session = await db.execute(
        select(UserSessionModel).where(UserSessionModel.session_token == token)
    )
    session = session.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()
    
    return {"message": "Logged out successfully"}


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    },
    summary="현재 사용자 정보 조회",
    description="현재 인증된 사용자의 정보를 반환합니다.",
)
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user),
):
    """현재 사용자 정보 조회"""
    return UserResponse(
        userId=current_user.user_id,
        email=current_user.email,
        name=current_user.name,
        orgId=current_user.org_id,
        role=current_user.role,
        avatarUrl=current_user.avatar_url,
    )


# ============================================================
# 2FA 엔드포인트
# ============================================================

@router.post(
    "/2fa/setup",
    response_model=Setup2FAResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        409: {"model": ErrorResponse, "description": "2FA already enabled"},
    },
    summary="2FA 설정",
    description="TOTP 기반 2FA 설정을 시작합니다.",
)
async def setup_2fa(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    2FA 설정 시작
    
    Returns:
        - provisioning_uri: QR 코드 생성용 URI (Google Authenticator 등)
        - backup_codes: 백업 코드 목록 (1회만 표시)
    """
    # 이미 활성화된 경우
    if hasattr(current_user, 'totp_enabled') and current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "2FA already enabled", "code": "2FA_ALREADY_ENABLED"},
        )
    
    # 2FA 설정 생성
    two_fa_service = get_2fa_service()
    setup_data = two_fa_service.setup_2fa(current_user.user_id, current_user.email)
    
    # 임시로 시크릿 저장 (확인 전까지 활성화되지 않음)
    if hasattr(current_user, 'totp_secret_pending'):
        current_user.totp_secret_pending = setup_data["secret"]
    
    # 백업 코드 해시만 저장
    backup_codes_plain = [code for code, _ in setup_data["backup_codes"]]
    backup_codes_hashes = [hash for _, hash in setup_data["backup_codes"]]
    
    if hasattr(current_user, 'backup_code_hashes_pending'):
        current_user.backup_code_hashes_pending = backup_codes_hashes
    
    await db.commit()
    
    logger.info(f"2FA setup initiated for user: {current_user.user_id}")
    
    return Setup2FAResponse(
        secret=setup_data["secret"],
        provisioning_uri=setup_data["provisioning_uri"],
        backup_codes=backup_codes_plain,
    )


@router.post(
    "/2fa/verify",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid code"},
    },
    summary="2FA 활성화 확인",
    description="TOTP 코드로 2FA 설정을 확인하고 활성화합니다.",
)
async def verify_2fa_setup(
    request: Verify2FARequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    2FA 설정 확인
    
    사용자가 앱에 등록 후 코드를 입력하여 확인
    확인 완료 시 2FA 활성화
    """
    # 대기 중인 시크릿 확인
    if not hasattr(current_user, 'totp_secret_pending') or not current_user.totp_secret_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "2FA setup not initiated", "code": "NO_2FA_PENDING"},
        )
    
    # 코드 검증
    two_fa_service = get_2fa_service()
    if not two_fa_service.verify_2fa_setup(current_user.totp_secret_pending, request.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid verification code", "code": "INVALID_CODE"},
        )
    
    # 2FA 활성화
    current_user.totp_secret = current_user.totp_secret_pending
    current_user.totp_enabled = True
    current_user.totp_secret_pending = None
    
    if hasattr(current_user, 'backup_code_hashes_pending'):
        current_user.backup_code_hashes = current_user.backup_code_hashes_pending
        current_user.backup_code_hashes_pending = None
    
    await db.commit()
    
    logger.info(f"2FA enabled for user: {current_user.user_id}")
    
    return {"message": "2FA enabled successfully"}


@router.post(
    "/2fa/disable",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid code"},
    },
    summary="2FA 비활성화",
    description="2FA를 비활성화합니다 (코드 확인 필요).",
)
async def disable_2fa(
    request: Verify2FARequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    2FA 비활성화
    
    현재 TOTP 코드 또는 백업 코드로 확인 후 비활성화
    """
    # 2FA 활성화 확인
    if not hasattr(current_user, 'totp_enabled') or not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "2FA not enabled", "code": "2FA_NOT_ENABLED"},
        )
    
    # 코드 검증
    two_fa_service = get_2fa_service()
    verified, _ = two_fa_service.verify_2fa_login(
        current_user.totp_secret,
        request.code,
        current_user.backup_code_hashes if hasattr(current_user, 'backup_code_hashes') else None,
    )
    
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid verification code", "code": "INVALID_CODE"},
        )
    
    # 2FA 비활성화
    current_user.totp_secret = None
    current_user.totp_enabled = False
    current_user.backup_code_hashes = None
    
    await db.commit()
    
    logger.info(f"2FA disabled for user: {current_user.user_id}")
    
    return {"message": "2FA disabled successfully"}
