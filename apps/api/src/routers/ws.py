"""
WebSocket 라우터
- WS /ws/workspaces/{wsId}
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from typing import Dict, Set
import json
from ..models import WSMessageType, WSMessage

router = APIRouter(tags=["websocket"])

# 연결된 클라이언트 관리
# TODO: Redis pub/sub으로 다중 인스턴스 지원
connected_clients: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """WebSocket 연결 관리자"""
    
    def __init__(self):
        # workspace_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, workspace_id: str):
        """새 연결 수락"""
        await websocket.accept()
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = set()
        self.active_connections[workspace_id].add(websocket)
    
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
        """워크스페이스 내 브로드캐스트"""
        if workspace_id not in self.active_connections:
            return
        for connection in self.active_connections[workspace_id]:
            if connection != exclude:
                try:
                    await connection.send_json(message)
                except Exception:
                    # 연결이 끊긴 경우 무시
                    pass


manager = ConnectionManager()


def _validate_workspace_access(ws_id: str, token: str = None) -> bool:
    """워크스페이스 접근 권한 검증"""
    # TODO: 실제 권한 검증 로직 구현
    # - 토큰 검증
    # - 워크스페이스 접근 권한 확인
    return True


@router.websocket("/ws/workspaces/{ws_id}")
async def websocket_endpoint(websocket: WebSocket, ws_id: str):
    """
    워크스페이스 WebSocket 연결
    
    메시지 타입:
    - file_change: 파일 변경 알림
    - cursor_move: 커서 이동 (협업용)
    - ai_stream: AI 응답 스트리밍
    - error: 에러 메시지
    
    TODO: 실제 기능 구현
    - 인증 토큰 검증 (query param 또는 첫 메시지)
    - 파일 변경 감지 및 브로드캐스트
    - AI 응답 스트리밍
    - 협업 기능 (커서 위치 공유)
    
    TODO: 스케일링
    - Redis pub/sub으로 다중 인스턴스 지원
    - 메시지 큐 연동
    """
    # TODO: 인증 검증
    # token = websocket.query_params.get("token")
    # if not _validate_workspace_access(ws_id, token):
    #     await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    #     return
    
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
                    # TODO: 파일 변경 처리
                    # - 변경 내용 검증
                    # - 다른 클라이언트에 브로드캐스트
                    await manager.broadcast(
                        {"type": msg_type, "payload": payload},
                        ws_id,
                        exclude=websocket,
                    )
                    
                elif msg_type == WSMessageType.CURSOR_MOVE.value:
                    # TODO: 커서 이동 처리 (협업)
                    await manager.broadcast(
                        {"type": msg_type, "payload": payload},
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
