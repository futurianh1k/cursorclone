"""
워크스페이스 배치 서비스
서버 선택 알고리즘 및 배치 관리
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from datetime import datetime

from ..db.models import (
    InfrastructureServerModel,
    WorkspacePlacementModel,
    WorkspaceModel,
)


class PlacementService:
    """워크스페이스 배치 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def select_server(
        self,
        policy: str = "least_loaded",
        region: Optional[str] = None,
    ) -> Optional[InfrastructureServerModel]:
        """
        정책 기반 서버 선택
        
        Args:
            policy: 배치 정책 (least_loaded, round_robin, region_based)
            region: 지역 필터 (선택사항)
        
        Returns:
            선택된 서버 또는 None
        """
        query = select(InfrastructureServerModel).where(
            InfrastructureServerModel.status == "active"
        )
        
        if region:
            query = query.where(InfrastructureServerModel.region == region)
        
        result = await self.db.execute(query)
        servers = result.scalars().all()
        
        if not servers:
            return None
        
        if policy == "least_loaded":
            return await self._select_least_loaded(servers)
        elif policy == "round_robin":
            return await self._select_round_robin(servers)
        elif policy == "region_based":
            return await self._select_region_based(servers, region)
        else:
            # 기본값: least_loaded
            return await self._select_least_loaded(servers)
    
    async def _select_least_loaded(self, servers: list) -> InfrastructureServerModel:
        """가장 적은 부하를 가진 서버 선택"""
        # CPU 사용률 기준으로 정렬
        def get_cpu_usage_ratio(server):
            if server.cpu_capacity and server.cpu_capacity > 0:
                return float(server.cpu_usage or 0) / float(server.cpu_capacity)
            return 1.0
        
        servers_sorted = sorted(servers, key=get_cpu_usage_ratio)
        return servers_sorted[0]
    
    async def _select_round_robin(self, servers: list) -> InfrastructureServerModel:
        """라운드 로빈 방식으로 서버 선택"""
        # TODO: Redis에서 마지막 선택 서버 ID 가져오기
        # 현재는 첫 번째 서버 반환
        return servers[0]
    
    async def _select_region_based(self, servers: list, region: Optional[str]) -> InfrastructureServerModel:
        """지역 기반 서버 선택"""
        if region:
            # 같은 지역의 서버 우선 선택
            region_servers = [s for s in servers if s.region == region]
            if region_servers:
                return await self._select_least_loaded(region_servers)
        
        # 지역이 없거나 같은 지역 서버가 없으면 least_loaded
        return await self._select_least_loaded(servers)
    
    async def place_workspace(
        self,
        workspace_id: str,
        server_id: UUID,
        policy: str = "auto",
    ) -> WorkspacePlacementModel:
        """
        워크스페이스 배치
        
        Args:
            workspace_id: 워크스페이스 ID
            server_id: 서버 ID
            policy: 배치 정책
        
        Returns:
            배치 정보
        """
        # 기존 배치 확인
        existing = await self.db.execute(
            select(WorkspacePlacementModel).where(
                WorkspacePlacementModel.workspace_id == workspace_id
            )
        )
        existing_placement = existing.scalar_one_or_none()
        
        if existing_placement:
            # 기존 배치 업데이트
            existing_placement.server_id = server_id
            existing_placement.placement_policy = policy
            existing_placement.placed_at = datetime.utcnow()
            await self.db.flush()
            return existing_placement
        
        # 새 배치 생성
        placement = WorkspacePlacementModel(
            workspace_id=workspace_id,
            server_id=server_id,
            placement_policy=policy,
        )
        self.db.add(placement)
        
        # 서버의 현재 워크스페이스 수 증가
        server = await self.db.get(InfrastructureServerModel, server_id)
        if server:
            server.current_workspaces = (server.current_workspaces or 0) + 1
        
        await self.db.flush()
        return placement
