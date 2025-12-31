"""
SSE (Server-Sent Events) 유틸리티
Task D: vLLM Router 구현 - Streaming 응답을 SSE로 프록시
"""

from fastapi import Response
from fastapi.responses import StreamingResponse
from typing import AsyncIterator
import json


def create_sse_response(stream: AsyncIterator[str]) -> StreamingResponse:
    """
    SSE 응답 생성
    
    Args:
        stream: 텍스트 스트림 (AsyncIterator[str])
        
    Returns:
        SSE StreamingResponse
    """
    async def sse_generator():
        """SSE 형식으로 변환"""
        async for chunk in stream:
            # SSE 형식: "data: {content}\n\n"
            data = json.dumps({"content": chunk})
            yield f"data: {data}\n\n"
        
        # 종료 신호
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성화
        },
    )


def create_sse_chunk(content: str, event: str = "message") -> str:
    """
    SSE 청크 생성
    
    Args:
        content: 내용
        event: 이벤트 타입
        
    Returns:
        SSE 형식 문자열
    """
    data = json.dumps({"content": content})
    return f"event: {event}\ndata: {data}\n\n"
