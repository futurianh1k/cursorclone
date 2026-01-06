"""add projects table and workspace project_id

Revision ID: 97af3d80270c
Revises: 0002
Create Date: 2026-01-07 02:06:36.649961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '97af3d80270c'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # gen_random_uuid()를 위해 pgcrypto 확장 사용
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # NOTE:
    # - 운영 중/PoC 환경에서 부분 적용/수동 생성 등으로 스키마가 이미 존재할 수 있어
    #   본 마이그레이션은 가능한 한 idempotent하게 동작하도록 IF NOT EXISTS 기반 DDL을 사용합니다.

    # 1) projects 테이블 생성(이미 있으면 스킵)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
          id uuid NOT NULL,
          project_id varchar(100) NOT NULL,
          name varchar(255) NOT NULL,
          owner_id varchar(100) NOT NULL,
          org_id varchar(100),
          created_at timestamptz DEFAULT now(),
          updated_at timestamptz,
          PRIMARY KEY (id),
          CONSTRAINT projects_project_id_key UNIQUE (project_id),
          CONSTRAINT projects_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(user_id),
          CONSTRAINT projects_org_id_fkey FOREIGN KEY (org_id) REFERENCES organizations(org_id)
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_projects_project_id ON projects(project_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_owner_created ON projects(owner_id, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_project_org_created ON projects(org_id, created_at);")

    # 2) workspaces.project_id 추가 (처음엔 nullable)
    op.execute("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS project_id varchar(100);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workspaces_project_id ON workspaces(project_id);")

    # 3) 기존 데이터 backfill
    # - 기존 workspace는 모두 "workspace별 1 project"로 승격(데이터 보존 우선)
    # - project_id는 "prj_{workspace_id}"로 생성하여 충돌 방지
    op.execute(
        """
        INSERT INTO projects (id, project_id, name, owner_id, org_id, created_at)
        SELECT
          gen_random_uuid(),
          'prj_' || w.workspace_id,
          w.name,
          w.owner_id,
          w.org_id,
          w.created_at
        FROM workspaces w
        WHERE w.project_id IS NULL
        ON CONFLICT (project_id) DO NOTHING;
        """
    )
    op.execute(
        """
        UPDATE workspaces
        SET project_id = 'prj_' || workspace_id
        WHERE project_id IS NULL;
        """
    )

    # 4) FK 추가 (이미 있으면 스킵)
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'fk_workspaces_project_id'
          ) THEN
            ALTER TABLE workspaces
              ADD CONSTRAINT fk_workspaces_project_id
              FOREIGN KEY (project_id) REFERENCES projects(project_id)
              ON DELETE RESTRICT;
          END IF;
        END $$;
        """
    )

    # 5) 인덱스 및 NOT NULL로 고정
    op.execute("CREATE INDEX IF NOT EXISTS idx_workspace_project_status ON workspaces(project_id, status);")
    op.execute("ALTER TABLE workspaces ALTER COLUMN project_id SET NOT NULL;")


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("workspaces", "project_id", existing_type=sa.String(length=100), nullable=True)
    op.drop_index("idx_workspace_project_status", table_name="workspaces")
    op.drop_constraint("fk_workspaces_project_id", "workspaces", type_="foreignkey")
    op.drop_index("ix_workspaces_project_id", table_name="workspaces")
    op.drop_column("workspaces", "project_id")

    op.drop_index("idx_project_org_created", table_name="projects")
    op.drop_index("idx_project_owner_created", table_name="projects")
    op.drop_index("ix_projects_project_id", table_name="projects")
    op.drop_table("projects")
