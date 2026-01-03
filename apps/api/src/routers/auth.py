"""
Auth 라우터
- POST /api/auth/signup (회원가입)
- POST /api/auth/login (로그인)
- POST /api/auth/logout (로그아웃)
- GET /api/auth/me (현재 사용자 정보)
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime, timedelta
import secrets

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

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


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
    password_hash = password_service.hash_password(request.password)
    
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
    },
    summary="로그인",
    description="사용자 로그인",
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    http_request: Request = None,
):
    """로그인"""
    # 사용자 조회
    user = await db.execute(
        select(UserModel).where(UserModel.email == request.email.lower())
    )
    user = user.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "Invalid email or password", "code": "INVALID_CREDENTIALS"},
        )
    
    # 비밀번호 검증
    if user.password_hash:
        if not password_service.verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "Invalid email or password", "code": "INVALID_CREDENTIALS"},
            )
    
    # 마지막 로그인 시간 업데이트
    user.last_login_at = datetime.utcnow()
    
    # JWT 토큰 생성
    access_token = jwt_auth_service.create_access_token(user.user_id, user.email)
    
    # 세션 생성
    session_token = secrets.token_urlsafe(32)
    ip_address = http_request.client.host if http_request else None
    user_agent = http_request.headers.get("user-agent") if http_request else None
    
    session = UserSessionModel(
        user_id=user.user_id,
        session_token=session_token,
        expires_at=datetime.utcnow() + timedelta(days=30),
        ip_address=ip_address,
        user_agent=user_agent,
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
