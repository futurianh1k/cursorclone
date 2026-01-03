"""
WebSocket 라우터
- WS /ws/workspaces/{wsId}

다중 인스턴스 지원:
- REDIS_URL 환경변수 설정 시 Redis pub/sub 사용
- 미설정 시 로컬 메모리 모드 (단일 인스턴스)
"""

import logging
import os
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from typing import Dict, Set, Optional
import json
from ..models import WSMessageType, WSMessage
from ..services.auth_service import jwt_auth_service

logger = logging.getLogger(__name__)

# Redis 설정
REDIS_URL = os.getenv("REDIS_URL")  # 예: redis://localhost:6379

# Redis 클라이언트 (선택적)
redis_client = None
redis_pubsub = None

if REDIS_URL:
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
        logger.info(f"Redis pub/sub enabled: {REDIS_URL}")
    except ImportError:
        logger.warning("redis package not installed. Using local mode.")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Using local mode.")

router = APIRouter(tags=["websocket"])

# 연결된 클라이언트 관리 (로컬 메모리)
connected_clients: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """
    WebSocket 연결 관리자
    
    다중 인스턴스 지원:
    - Redis pub/sub 활성화 시: 다른 인스턴스로 메시지 전파
    - 로컬 모드: 현재 인스턴스 내 클라이언트만
    """
    
    def __init__(self):
        # workspace_id -> set of websockets (로컬 연결)
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._pubsub_task: Optional[asyncio.Task] = None
    
    async def connect(self, websocket: WebSocket, workspace_id: str):
        """새 연결 수락"""
        await websocket.accept()
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = set()
        self.active_connections[workspace_id].add(websocket)
        
        # Redis pub/sub 구독 시작 (첫 연결 시)
        if redis_client and not self._pubsub_task:
            self._pubsub_task = asyncio.create_task(self._redis_subscriber())
    
    def disconnect(self, websocket: WebSocket, workspace_id: str):
        """연결 종료"""
        if workspace_id in self.active_connections:
            self.active_connections[workspace_id].discard(websocket)
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]
    
    async def send_personal(self, message: dict, websocket: WebSocket):
        """개인 메시지 전송"""
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict, workspace_id: str, exclude: WebSocket = None):
        """
        워크스페이스 내 브로드캐스트
        
        Redis 활성화 시: pub/sub으로 다른 인스턴스에도 전파
        """
        # 로컬 브로드캐스트
        await self._broadcast_local(message, workspace_id, exclude)
        
        # Redis pub/sub으로 다른 인스턴스에 전파
        if redis_client:
            try:
                channel = f"ws:workspace:{workspace_id}"
                await redis_client.publish(channel, json.dumps(message))
            except Exception as e:
                logger.error(f"Redis publish failed: {e}")
    
    async def _broadcast_local(self, message: dict, workspace_id: str, exclude: WebSocket = None):
        """로컬 인스턴스 내 브로드캐스트"""
        if workspace_id not in self.active_connections:
            return
        for connection in self.active_connections[workspace_id]:
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except Exception:
                    # 연결이 끊긴 경우 무시
                    pass
    
    async def _redis_subscriber(self):
        """Redis pub/sub 구독자 (백그라운드 태스크)"""
        if not redis_client:
            return
        
        try:
            pubsub = redis_client.pubsub()
            # 모든 워크스페이스 채널 패턴 구독
            await pubsub.psubscribe("ws:workspace:*")
            
            logger.info("Redis pub/sub subscriber started")
            
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    try:
                        # 채널에서 workspace_id 추출
                        channel = message["channel"]
                        workspace_id = channel.split(":")[-1]
                        data = json.loads(message["data"])
                        
                        # 로컬 클라이언트에 전달 (exclude 없음 - 다른 인스턴스에서 온 메시지)
                        await self._broadcast_local(data, workspace_id)
                    except Exception as e:
                        logger.error(f"Redis message processing failed: {e}")
                        
        except asyncio.CancelledError:
            logger.info("Redis pub/sub subscriber cancelled")
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")


manager = ConnectionManager()


def _validate_token(token: Optional[str]) -> Optional[dict]:
    """
    JWT 토큰 검증
    
    Returns:
        유효한 경우 페이로드 dict, 그렇지 않으면 None
    """
    if not token:
        return None
    
    try:
        payload = jwt_auth_service.verify_token(token)
        return payload
    except Exception as e:
        logger.warning(f"WebSocket token validation failed: {e}")
        return None


def _validate_workspace_access(ws_id: str, user_id: str) -> bool:
    """
    워크스페이스 접근 권한 검증
    
    사용자가 해당 워크스페이스에 접근할 수 있는지 확인합니다.
    """
    # TODO: DB에서 워크스페이스 소유권/공유 관계 확인
    # 현재 PoC에서는 기본적으로 허용
    return True


@router.websocket("/ws/workspaces/{ws_id}")
async def websocket_endpoint(websocket: WebSocket, ws_id: str):
    """
    워크스페이스 WebSocket 연결
    
    인증: Query parameter `token`에 JWT 토큰 전달
    예: ws://host/ws/workspaces/ws_my-project?token=eyJ...
    
    메시지 타입:
    - file_change: 파일 변경 알림
    - cursor_move: 커서 이동 (협업용)
    - ai_stream: AI 응답 스트리밍
    - error: 에러 메시지
    
    TODO: 스케일링
    - Redis pub/sub으로 다중 인스턴스 지원
    - 메시지 큐 연동
    """
    # 인증 검증 (query parameter에서 토큰 추출)
    token = websocket.query_params.get("token")
    payload = _validate_token(token)
    
    if not payload:
        logger.warning(f"WebSocket connection rejected: invalid token for workspace {ws_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    user_id = payload.get("sub", "anonymous")
    
    # 워크스페이스 접근 권한 확인
    if not _validate_workspace_access(ws_id, user_id):
        logger.warning(f"WebSocket connection rejected: no access to workspace {ws_id} for user {user_id}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    logger.info(f"WebSocket connected: user={user_id}, workspace={ws_id}")
    await manager.connect(websocket, ws_id)
    
    try:
        # 연결 성공 메시지
        await manager.send_personal(
            {
                "type": WSMessageType.FILE_CHANGE.value,
                "payload": {
                    "event": "connected",
                    "workspace_id": ws_id,
                    "message": "WebSocket connected (stub)",
                },
            },
            websocket,
        )
        
        while True:
            # 클라이언트 메시지 수신
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                payload = message.get("payload", {})
                
                # 메시지 타입별 처리
                if msg_type == WSMessageType.FILE_CHANGE.value:
                    # 파일 변경 처리
                    file_path = payload.get("file_path", "")
                    change_type = payload.get("change_type", "modify")  # create, modify, delete
                    content = payload.get("content")
                    
                    # 경로 검증 (보안)
                    if ".." in file_path or file_path.startswith("/"):
                        await manager.send_personal(
                            {
                                "type": WSMessageType.ERROR.value,
                                "payload": {
                                    "error": "Invalid file path",
                                    "code": "WS_INVALID_PATH",
                                },
                            },
                            websocket,
                        )
                        continue
                    
                    # 변경 내용에 사용자 정보 추가
                    enriched_payload = {
                        **payload,
                        "user_id": user_id,
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                    
                    # 다른 클라이언트에 브로드캐스트
                    await manager.broadcast(
                        {"type": msg_type, "payload": enriched_payload},
                        ws_id,
                        exclude=websocket,
                    )
                    
                    logger.debug(f"File change broadcast: {change_type} {file_path} by {user_id}")
                    
                elif msg_type == WSMessageType.CURSOR_MOVE.value:
                    # 커서 이동 처리 (협업)
                    file_path = payload.get("file_path", "")
                    line = payload.get("line", 0)
                    column = payload.get("column", 0)
                    selection = payload.get("selection")  # {start: {line, col}, end: {line, col}}
                    
                    # 커서 정보에 사용자 정보 추가
                    cursor_payload = {
                        "user_id": user_id,
                        "file_path": file_path,
                        "line": line,
                        "column": column,
                        "selection": selection,
                        "timestamp": asyncio.get_event_loop().time(),
                    }
                    
                    # 다른 클라이언트에 브로드캐스트
                    await manager.broadcast(
                        {"type": msg_type, "payload": cursor_payload},
                        ws_id,
                        exclude=websocket,
                    )
                    
                else:
                    # 알 수 없는 메시지 타입
                    await manager.send_personal(
                        {
                            "type": WSMessageType.ERROR.value,
                            "payload": {
                                "error": "Unknown message type",
                                "code": "WS_UNKNOWN_TYPE",
                            },
                        },
                        websocket,
                    )
                    
            except json.JSONDecodeError:
                await manager.send_personal(
                    {
                        "type": WSMessageType.ERROR.value,
                        "payload": {
                            "error": "Invalid JSON",
                            "code": "WS_INVALID_JSON",
                        },
                    },
                    websocket,
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, ws_id)
