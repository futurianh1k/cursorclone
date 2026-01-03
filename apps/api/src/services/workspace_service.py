"""
워크스페이스 서비스
비즈니스 로직 분리 및 데이터베이스 연동
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from datetime import datetime

from ..db.models import (
    WorkspaceModel,
    UserModel,
    OrganizationModel,
    WorkspaceResourceModel,
)
from ..services.cache_service import cache_service


class WorkspaceService:
    """워크스페이스 비즈니스 로직 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_workspace(
        self,
        name: str,
        owner_id: str,
        org_id: Optional[str] = None,
        root_path: Optional[str] = None,
    ) -> WorkspaceModel:
        """워크스페이스 생성"""
        workspace_id = f"ws_{name}"
        
        # 중복 확인
        existing = await self.db.execute(
            select(WorkspaceModel).where(WorkspaceModel.workspace_id == workspace_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Workspace {workspace_id} already exists")
        
        # 워크스페이스 생성
        workspace = WorkspaceModel(
            workspace_id=workspace_id,
            name=name,
            owner_id=owner_id,
            org_id=org_id,
            root_path=root_path or f"/workspaces/{workspace_id}",
            status="stopped",
        )
        
        self.db.add(workspace)
        await self.db.flush()
        
        # 캐시 무효화
        await cache_service.invalidate_workspace_list(owner_id)
        
        return workspace
    
    async def get_workspace(self, workspace_id: str) -> Optional[WorkspaceModel]:
        """워크스페이스 조회"""
        result = await self.db.execute(
            select(WorkspaceModel).where(WorkspaceModel.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()
    
    async def list_workspaces(
        self,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[WorkspaceModel]:
        """워크스페이스 목록 조회 (캐싱 지원)"""
        
        # 캐시 키 생성
        cache_key = f"workspace:list:{user_id or 'all'}:{org_id or 'all'}:{status or 'all'}"
        
        # 캐시 조회
        cached = await cache_service.get(cache_key)
        if cached:
            # 캐시된 데이터를 모델로 변환 (간단한 딕셔너리로 저장하는 경우)
            # 실제로는 ID만 캐시하고 DB에서 조회하는 것이 더 안전
            pass
        
        # 쿼리 구성
        query = select(WorkspaceModel)
        
        if user_id:
            query = query.where(WorkspaceModel.owner_id == user_id)
        if org_id:
            query = query.where(WorkspaceModel.org_id == org_id)
        if status:
            query = query.where(WorkspaceModel.status == status)
        
        query = query.order_by(WorkspaceModel.created_at.desc())
        
        result = await self.db.execute(query)
        workspaces = result.scalars().all()
        
        # 캐시 저장 (5분 TTL)
        workspace_data = [
            {
                "workspace_id": ws.workspace_id,
                "name": ws.name,
                "owner_id": ws.owner_id,
                "org_id": ws.org_id,
                "status": ws.status,
                "root_path": ws.root_path,
            }
            for ws in workspaces
        ]
        await cache_service.set(cache_key, workspace_data, ttl=300)
        
        return workspaces
    
    async def update_workspace_status(
        self,
        workspace_id: str,
        status: str,
        container_id: Optional[str] = None,
    ):
        """워크스페이스 상태 업데이트"""
        await self.db.execute(
            update(WorkspaceModel)
            .where(WorkspaceModel.workspace_id == workspace_id)
            .values(
                status=status,
                container_id=container_id,
                updated_at=datetime.utcnow(),
            )
        )
        await self.db.flush()
        
        # 캐시 무효화
        workspace = await self.get_workspace(workspace_id)
        if workspace:
            await cache_service.invalidate_workspace_list(workspace.owner_id)
    
    async def update_last_accessed(self, workspace_id: str):
        """마지막 접근 시간 업데이트 (자동 정지용)"""
        await self.db.execute(
            update(WorkspaceModel)
            .where(WorkspaceModel.workspace_id == workspace_id)
            .values(last_accessed_at=datetime.utcnow())
        )
        await self.db.flush()
    
    async def delete_workspace(self, workspace_id: str):
        """워크스페이스 삭제 (소프트 삭제)"""
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return

        await self.update_workspace_status(workspace_id, "deleted")

        # 캐시 무효화
        await cache_service.invalidate_workspace_list(workspace.owner_id)
        await cache_service.invalidate_file_tree(workspace_id)

    async def hard_delete_workspace(self, workspace_id: str) -> bool:
        """
        워크스페이스 완전 삭제 (데이터베이스에서 영구 삭제)

        Args:
            workspace_id: 삭제할 워크스페이스 ID

        Returns:
            bool: 삭제 성공 여부
        """
        workspace = await self.get_workspace(workspace_id)
        if not workspace:
            return False

        owner_id = workspace.owner_id

        # 관련 리소스 메타데이터 삭제
        await self.db.execute(
            delete(WorkspaceResourceModel).where(
                WorkspaceResourceModel.workspace_id == workspace_id
            )
        )

        # 워크스페이스 삭제
        await self.db.execute(
            delete(WorkspaceModel).where(
                WorkspaceModel.workspace_id == workspace_id
            )
        )

        await self.db.flush()

        # 캐시 무효화
        await cache_service.invalidate_workspace_list(owner_id)
        await cache_service.invalidate_file_tree(workspace_id)

        return True
