"""
중앙 로깅 시스템 연동 서비스

지원 시스템:
- Elasticsearch (ELK Stack)
- Loki (Grafana)
- Splunk (HEC)

환경변수로 활성화:
- LOGGING_BACKEND: elasticsearch, loki, splunk, none (기본: none)
- ELASTICSEARCH_URL: Elasticsearch URL
- LOKI_URL: Loki Push API URL
- SPLUNK_HEC_URL: Splunk HEC URL
- SPLUNK_HEC_TOKEN: Splunk HEC 토큰
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import asyncio

logger = logging.getLogger(__name__)

# 환경 설정
LOGGING_BACKEND = os.getenv("LOGGING_BACKEND", "none")  # elasticsearch, loki, splunk, none
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "cursor-poc-logs")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100/loki/api/v1/push")
SPLUNK_HEC_URL = os.getenv("SPLUNK_HEC_URL", "https://localhost:8088/services/collector")
SPLUNK_HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN", "")


class CentralLoggingService:
    """중앙 로깅 시스템 연동 서비스"""
    
    def __init__(self):
        self.backend = LOGGING_BACKEND
        self._http_client = None
        
        if self.backend != "none":
            logger.info(f"Central logging enabled: {self.backend}")
    
    async def _get_client(self):
        """HTTP 클라이언트 가져오기 (lazy init)"""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client
    
    async def log(
        self,
        level: str,
        message: str,
        *,
        service: str = "cursor-api",
        user_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        action: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        중앙 로깅 시스템에 로그 전송
        
        Args:
            level: 로그 레벨 (info, warning, error, audit)
            message: 로그 메시지
            service: 서비스 이름
            user_id: 사용자 ID
            workspace_id: 워크스페이스 ID
            action: 수행한 작업
            extra: 추가 메타데이터
        """
        if self.backend == "none":
            return
        
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "service": service,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "action": action,
            **(extra or {}),
        }
        
        try:
            if self.backend == "elasticsearch":
                await self._send_to_elasticsearch(log_entry)
            elif self.backend == "loki":
                await self._send_to_loki(log_entry)
            elif self.backend == "splunk":
                await self._send_to_splunk(log_entry)
        except Exception as e:
            logger.error(f"Failed to send log to {self.backend}: {e}")
    
    async def _send_to_elasticsearch(self, log_entry: Dict[str, Any]):
        """Elasticsearch로 로그 전송"""
        client = await self._get_client()
        
        # 인덱스 이름에 날짜 추가 (일별 롤링)
        date_suffix = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        index_name = f"{ELASTICSEARCH_INDEX}-{date_suffix}"
        
        response = await client.post(
            f"{ELASTICSEARCH_URL}/{index_name}/_doc",
            json=log_entry,
            headers={"Content-Type": "application/json"},
        )
        
        if response.status_code not in (200, 201):
            logger.warning(f"Elasticsearch response: {response.status_code}")
    
    async def _send_to_loki(self, log_entry: Dict[str, Any]):
        """Loki로 로그 전송"""
        client = await self._get_client()
        
        # Loki 형식으로 변환
        labels = {
            "service": log_entry.get("service", "cursor-api"),
            "level": log_entry.get("level", "info"),
        }
        
        if log_entry.get("user_id"):
            labels["user_id"] = log_entry["user_id"]
        if log_entry.get("workspace_id"):
            labels["workspace_id"] = log_entry["workspace_id"]
        
        # nanoseconds timestamp
        ts = int(datetime.now(timezone.utc).timestamp() * 1e9)
        
        loki_payload = {
            "streams": [
                {
                    "stream": labels,
                    "values": [
                        [str(ts), json.dumps(log_entry)]
                    ]
                }
            ]
        }
        
        response = await client.post(
            LOKI_URL,
            json=loki_payload,
            headers={"Content-Type": "application/json"},
        )
        
        if response.status_code not in (200, 204):
            logger.warning(f"Loki response: {response.status_code}")
    
    async def _send_to_splunk(self, log_entry: Dict[str, Any]):
        """Splunk HEC로 로그 전송"""
        if not SPLUNK_HEC_TOKEN:
            logger.warning("Splunk HEC token not configured")
            return
        
        client = await self._get_client()
        
        splunk_payload = {
            "event": log_entry,
            "sourcetype": "cursor-api",
            "source": log_entry.get("service", "cursor-api"),
            "index": "main",
        }
        
        response = await client.post(
            SPLUNK_HEC_URL,
            json=splunk_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
            },
            verify=False,  # PoC용 SSL 검증 비활성화
        )
        
        if response.status_code != 200:
            logger.warning(f"Splunk response: {response.status_code}")
    
    async def audit(
        self,
        action: str,
        user_id: str,
        workspace_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        감사 로그 전송 (보안 이벤트)
        
        ISMS-P 및 금융권 감사 요구사항 대응
        """
        await self.log(
            level="audit",
            message=f"Audit: {action}",
            user_id=user_id,
            workspace_id=workspace_id,
            action=action,
            extra={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": details,
                "audit": True,
            },
        )
    
    async def close(self):
        """HTTP 클라이언트 종료"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# 싱글톤 인스턴스
central_logging = CentralLoggingService()


# FastAPI 라이프사이클 이벤트용
async def shutdown_logging():
    """애플리케이션 종료 시 로깅 클라이언트 정리"""
    await central_logging.close()
