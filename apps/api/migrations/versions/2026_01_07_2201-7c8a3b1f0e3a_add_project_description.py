"""add project description

Revision ID: 7c8a3b1f0e3a
Revises: 97af3d80270c
Create Date: 2026-01-07 22:01:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c8a3b1f0e3a"
down_revision = "97af3d80270c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # description 컬럼 추가 (nullable)
    op.add_column("projects", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "description")

