"""add workspace_file_index and workspace_symbols

Revision ID: 2026_01_08_0001
Revises: 7c8a3b1f0e3a
Create Date: 2026-01-08
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2026_01_08_0001"
down_revision = "7c8a3b1f0e3a"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    insp = sa.inspect(bind)
    return table_name in insp.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    # ----------------------------
    # workspace_file_index
    # ----------------------------
    if not _table_exists(bind, "workspace_file_index"):
        op.create_table(
            "workspace_file_index",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("org_id", sa.String(length=100), sa.ForeignKey("organizations.org_id"), nullable=True),
            sa.Column("project_id", sa.String(length=100), sa.ForeignKey("projects.project_id"), nullable=False),
            sa.Column("workspace_id", sa.String(length=100), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
            sa.Column("file_path", sa.String(length=1000), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("size_bytes", sa.BigInteger(), nullable=True),
            sa.Column("mtime_ns", sa.BigInteger(), nullable=True),
            sa.Column("indexed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_wfi_ws_path", "workspace_file_index", ["workspace_id", "file_path"], unique=True)
        op.create_index("idx_wfi_ws_updated", "workspace_file_index", ["workspace_id", "updated_at"], unique=False)
        op.create_index("idx_wfi_proj_updated", "workspace_file_index", ["project_id", "updated_at"], unique=False)
        op.create_index("ix_workspace_file_index_org_id", "workspace_file_index", ["org_id"], unique=False)
        op.create_index("ix_workspace_file_index_project_id", "workspace_file_index", ["project_id"], unique=False)
        op.create_index("ix_workspace_file_index_workspace_id", "workspace_file_index", ["workspace_id"], unique=False)

    # ----------------------------
    # workspace_symbols
    # ----------------------------
    if not _table_exists(bind, "workspace_symbols"):
        op.create_table(
            "workspace_symbols",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("org_id", sa.String(length=100), sa.ForeignKey("organizations.org_id"), nullable=True),
            sa.Column("project_id", sa.String(length=100), sa.ForeignKey("projects.project_id"), nullable=False),
            sa.Column("workspace_id", sa.String(length=100), sa.ForeignKey("workspaces.workspace_id", ondelete="CASCADE"), nullable=False),
            sa.Column("file_path", sa.String(length=1000), nullable=False),
            sa.Column("symbol_name", sa.String(length=255), nullable=False),
            sa.Column("symbol_kind", sa.String(length=50), nullable=False),
            sa.Column("start_line", sa.Integer(), nullable=True),
            sa.Column("end_line", sa.Integer(), nullable=True),
            sa.Column("signature", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_wsym_ws_name", "workspace_symbols", ["workspace_id", "symbol_name"], unique=False)
        op.create_index("idx_wsym_ws_file", "workspace_symbols", ["workspace_id", "file_path"], unique=False)
        op.create_index("idx_wsym_proj_name", "workspace_symbols", ["project_id", "symbol_name"], unique=False)
        op.create_index("ix_workspace_symbols_org_id", "workspace_symbols", ["org_id"], unique=False)
        op.create_index("ix_workspace_symbols_project_id", "workspace_symbols", ["project_id"], unique=False)
        op.create_index("ix_workspace_symbols_workspace_id", "workspace_symbols", ["workspace_id"], unique=False)
        op.create_index("ix_workspace_symbols_symbol_kind", "workspace_symbols", ["symbol_kind"], unique=False)
        op.create_index("ix_workspace_symbols_symbol_name", "workspace_symbols", ["symbol_name"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "workspace_symbols"):
        op.drop_table("workspace_symbols")
    if _table_exists(bind, "workspace_file_index"):
        op.drop_table("workspace_file_index")

