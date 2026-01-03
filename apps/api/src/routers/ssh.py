"""
SSH 라우터
워크스페이스 SSH 접속 관리 API

- GET /api/workspaces/{ws_id}/ssh/info     - SSH 연결 정보 조회
- POST /api/workspaces/{ws_id}/ssh/key     - SSH 공개키 설정
- POST /api/workspaces/{ws_id}/ssh/password - SSH 비밀번호 설정
- POST /api/workspaces/{ws_id}/ssh/generate - SSH 키 쌍 생성
"""

import os
import secrets
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends

from ..models import (
    ErrorResponse,
    SSHConnectionInfo,
    SSHConnectionResponse,
    SetupSSHKeyRequest,
    SetupSSHPasswordRequest,
    SSHKeyResponse,
    GenerateSSHKeyRequest,
    GenerateSSHKeyResponse,
)
from ..services.workspace_manager import get_workspace_manager, WorkspaceManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspaces/{ws_id}/ssh", tags=["ssh"])

# SSH 포트 범위 (동적 할당)
SSH_PORT_BASE = int(os.getenv("SSH_PORT_BASE", "22000"))
SSH_HOST = os.getenv("SSH_HOST", "localhost")  # 외부 접속 호스트


def _get_ssh_port(workspace_id: str) -> int:
    """워크스페이스 ID로 SSH 포트 계산 (해시 기반)"""
    # 워크스페이스 ID를 해시하여 일관된 포트 번호 생성
    hash_val = int(hashlib.md5(workspace_id.encode()).hexdigest()[:8], 16)
    return SSH_PORT_BASE + (hash_val % 1000)  # 22000 ~ 22999 범위


def _generate_ssh_command(host: str, port: int, username: str = "developer") -> str:
    """SSH 접속 명령어 생성"""
    return f"ssh -p {port} {username}@{host}"


def _generate_vscode_remote_uri(host: str, port: int, username: str = "developer", path: str = "/workspace") -> str:
    """VS Code Remote SSH URI 생성"""
    # vscode://vscode-remote/ssh-remote+user@host:port/path
    return f"vscode://vscode-remote/ssh-remote+{username}@{host}:{port}{path}"


def _get_ssh_key_fingerprint(public_key: str) -> str:
    """SSH 공개키 fingerprint 계산"""
    import base64
    try:
        # SSH 키의 두 번째 부분 (base64 인코딩된 부분)
        parts = public_key.strip().split()
        if len(parts) >= 2:
            key_data = base64.b64decode(parts[1])
            fingerprint = hashlib.sha256(key_data).digest()
            return "SHA256:" + base64.b64encode(fingerprint).decode().rstrip("=")
    except Exception:
        pass
    return "unknown"


@router.get(
    "/info",
    response_model=SSHConnectionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Workspace not found"},
        503: {"model": ErrorResponse, "description": "SSH not available"},
    },
    summary="SSH 연결 정보 조회",
    description="워크스페이스에 SSH로 접속하기 위한 연결 정보를 반환합니다.",
)
async def get_ssh_connection_info(
    ws_id: str,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
):
    """
    SSH 연결 정보 조회
    
    반환 정보:
    - 호스트, 포트, 사용자명
    - SSH 접속 명령어 (터미널용)
    - VS Code Remote SSH URI (Cursor/VS Code용)
    """
    # 컨테이너 상태 확인
    container_status = await workspace_manager.get_status(ws_id)
    
    if container_status.container_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace container not found", "code": "CONTAINER_NOT_FOUND"},
        )
    
    # SSH 포트 계산
    ssh_port = _get_ssh_port(ws_id)
    
    # 컨테이너가 실행 중인지 확인
    is_running = container_status.status.value == "running"
    
    connection = SSHConnectionInfo(
        host=SSH_HOST,
        port=ssh_port,
        username="developer",
        auth_type="key",  # 기본은 키 인증
    )
    
    ssh_command = _generate_ssh_command(SSH_HOST, ssh_port)
    vscode_uri = _generate_vscode_remote_uri(SSH_HOST, ssh_port)
    
    return SSHConnectionResponse(
        workspaceId=ws_id,
        connection=connection,
        status="available" if is_running else "unavailable",
        sshCommand=ssh_command,
        vscodeRemoteUri=vscode_uri,
    )


@router.post(
    "/key",
    response_model=SSHKeyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid SSH key"},
        404: {"model": ErrorResponse, "description": "Workspace not found"},
    },
    summary="SSH 공개키 설정",
    description="워크스페이스에 SSH 접속을 위한 공개키를 설정합니다.",
)
async def setup_ssh_key(
    ws_id: str,
    request: SetupSSHKeyRequest,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
):
    """
    SSH 공개키 설정
    
    사용자의 SSH 공개키를 워크스페이스 컨테이너의 authorized_keys에 추가합니다.
    """
    # 컨테이너 확인
    container = await workspace_manager.get_container(ws_id)
    if container is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace container not found", "code": "CONTAINER_NOT_FOUND"},
        )
    
    try:
        # authorized_keys에 공개키 추가
        public_key = request.public_key.strip()
        
        # 컨테이너 내에서 키 추가 명령 실행
        result = await workspace_manager.execute_command(
            workspace_id=ws_id,
            command=f'echo "{public_key}" >> /home/developer/.ssh/authorized_keys && chmod 600 /home/developer/.ssh/authorized_keys',
            timeout=10,
        )
        
        if result.exit_code != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": f"Failed to add SSH key: {result.stderr}", "code": "SSH_KEY_ADD_FAILED"},
            )
        
        fingerprint = _get_ssh_key_fingerprint(public_key)
        
        logger.info(f"SSH key added for workspace {ws_id}: {fingerprint}")
        
        return SSHKeyResponse(
            success=True,
            message="SSH public key added successfully",
            workspaceId=ws_id,
            fingerprint=fingerprint,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to setup SSH key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "code": "SSH_KEY_SETUP_FAILED"},
        )


@router.post(
    "/password",
    response_model=SSHKeyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid password"},
        404: {"model": ErrorResponse, "description": "Workspace not found"},
    },
    summary="SSH 비밀번호 설정",
    description="워크스페이스에 SSH 접속을 위한 비밀번호를 설정합니다.",
)
async def setup_ssh_password(
    ws_id: str,
    request: SetupSSHPasswordRequest,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
):
    """
    SSH 비밀번호 설정
    
    ⚠️ 보안 주의: 비밀번호 인증은 SSH 키 인증보다 보안이 낮습니다.
    가능하면 SSH 키 인증을 사용하세요.
    """
    # 컨테이너 확인
    container = await workspace_manager.get_container(ws_id)
    if container is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Workspace container not found", "code": "CONTAINER_NOT_FOUND"},
        )
    
    try:
        # 비밀번호 설정 (chpasswd 사용)
        result = await workspace_manager.execute_command(
            workspace_id=ws_id,
            command=f'echo "developer:{request.password}" | sudo chpasswd',
            timeout=10,
        )
        
        if result.exit_code != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": f"Failed to set SSH password: {result.stderr}", "code": "SSH_PASSWORD_SET_FAILED"},
            )
        
        logger.info(f"SSH password set for workspace {ws_id}")
        
        return SSHKeyResponse(
            success=True,
            message="SSH password set successfully",
            workspaceId=ws_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set SSH password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "code": "SSH_PASSWORD_SETUP_FAILED"},
        )


@router.post(
    "/generate",
    response_model=GenerateSSHKeyResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
    },
    summary="SSH 키 쌍 생성",
    description="새로운 SSH 키 쌍을 생성합니다. 개인키는 이 응답에서만 확인할 수 있습니다.",
)
async def generate_ssh_keypair(
    ws_id: str,
    request: GenerateSSHKeyRequest,
):
    """
    SSH 키 쌍 생성
    
    ⚠️ 중요: 개인키(private_key)는 이 응답에서만 확인할 수 있습니다.
    반드시 안전한 곳에 저장하세요.
    """
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
        from cryptography.hazmat.backends import default_backend
        
        comment = request.comment or f"cursor-workspace-{ws_id}"
        
        if request.key_type == "ed25519":
            # Ed25519 키 생성
            private_key = ed25519.Ed25519PrivateKey.generate()
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_key = private_key.public_key()
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH,
            )
        else:
            # RSA 키 생성 (4096 bits)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend(),
            )
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption(),
            )
            public_key = private_key.public_key()
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH,
            )
        
        public_key_str = public_bytes.decode() + f" {comment}"
        private_key_str = private_pem.decode()
        fingerprint = _get_ssh_key_fingerprint(public_key_str)
        
        logger.info(f"SSH keypair generated for workspace {ws_id}: {fingerprint}")
        
        return GenerateSSHKeyResponse(
            success=True,
            message="SSH keypair generated successfully. ⚠️ Save the private key now!",
            publicKey=public_key_str,
            privateKey=private_key_str,
            fingerprint=fingerprint,
        )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"error": "Cryptography library not available", "code": "CRYPTO_NOT_AVAILABLE"},
        )
    except Exception as e:
        logger.error(f"Failed to generate SSH keypair: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "code": "SSH_KEYGEN_FAILED"},
        )


@router.get(
    "/cursor-command",
    summary="Cursor Remote SSH 접속 명령어",
    description="Cursor IDE에서 Remote SSH 접속을 위한 설정 정보를 반환합니다.",
)
async def get_cursor_ssh_command(
    ws_id: str,
    workspace_manager: WorkspaceManager = Depends(get_workspace_manager),
):
    """
    Cursor IDE Remote SSH 접속 설정
    
    Cursor에서 Remote SSH 접속을 위한 설정 방법:
    1. Ctrl+Shift+P → "Remote-SSH: Connect to Host..."
    2. 반환된 SSH 명령어 입력
    3. 또는 VS Code 설정에 호스트 추가
    """
    ssh_port = _get_ssh_port(ws_id)
    
    return {
        "workspaceId": ws_id,
        "instructions": {
            "step1": "Cursor에서 Ctrl+Shift+P (macOS: Cmd+Shift+P) 실행",
            "step2": "'Remote-SSH: Connect to Host...' 선택",
            "step3": f"'{_generate_ssh_command(SSH_HOST, ssh_port)}' 입력",
        },
        "sshConfig": {
            "description": "~/.ssh/config에 추가할 설정",
            "content": f"""Host cursor-{ws_id}
    HostName {SSH_HOST}
    Port {ssh_port}
    User developer
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
""",
        },
        "vscodeRemoteUri": _generate_vscode_remote_uri(SSH_HOST, ssh_port),
        "directCommand": _generate_ssh_command(SSH_HOST, ssh_port),
    }
