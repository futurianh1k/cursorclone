"""
Projects 라우터
- POST /api/projects
- GET /api/projects
- GET /api/projects/{project_id}

설계 의도:
- 1 Project : N Workspaces
- project_id(pid)는 gateway 토큰/감사 로그의 핵심 스코프
"""

import secrets
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.connection import get_db
from ..db.models import ProjectModel, WorkspaceModel, UserModel
from ..models import CreateProjectRequest, ProjectResponse, WorkspaceResponse, ErrorResponse
from ..services.rbac_service import require_permission, Permission

router = APIRouter(prefix="/api/projects", tags=["projects"])
logger = logging.getLogger(__name__)


def _new_project_id(name: str) -> str:
    # 직관성 + 충돌 방지(짧은 suffix)
    suffix = secrets.token_urlsafe(4).replace("-", "").replace("_", "")
    safe = name.strip().lower().replace(" ", "-")
    safe = "".join(ch for ch in safe if ch.isalnum() or ch in "-_")
    safe = safe[:50] if safe else "project"
    return f"prj_{safe}_{suffix}"


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="프로젝트 생성",
)
async def create_project(
    request: CreateProjectRequest,
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    project_id = _new_project_id(request.name)

    project = ProjectModel(
        project_id=project_id,
        name=request.name,
        owner_id=current_user.user_id,
        org_id=current_user.org_id,
    )
    db.add(project)
    await db.commit()

    return ProjectResponse(
        projectId=project.project_id,
        name=project.name,
        ownerId=project.owner_id,
        orgId=project.org_id,
    )


@router.get(
    "",
    response_model=List[ProjectResponse],
    responses={401: {"model": ErrorResponse}},
    summary="프로젝트 목록 조회",
)
async def list_projects(
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    q = select(ProjectModel).where(ProjectModel.owner_id == current_user.user_id).order_by(ProjectModel.created_at.desc())
    res = await db.execute(q)
    projects = res.scalars().all()
    return [
        ProjectResponse(
            projectId=p.project_id,
            name=p.name,
            ownerId=p.owner_id,
            orgId=p.org_id,
        )
        for p in projects
    ]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    summary="프로젝트 조회",
)
async def get_project(
    project_id: str,
    current_user: UserModel = Depends(require_permission(Permission.WORKSPACE_READ)),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(ProjectModel).where(ProjectModel.project_id == project_id, ProjectModel.owner_id == current_user.user_id)
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail={"error": "Project not found", "code": "PROJECT_NOT_FOUND"})
    return ProjectResponse(projectId=p.project_id, name=p.name, ownerId=p.owner_id, orgId=p.org_id)

