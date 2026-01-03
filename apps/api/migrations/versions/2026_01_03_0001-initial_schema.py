"""Initial schema with optimized indexes

Revision ID: 0001
Revises: 
Create Date: 2026-01-03

이 마이그레이션은 Cursor On-Prem PoC의 초기 데이터베이스 스키마를 생성합니다.

테이블:
- organizations: 조직
- users: 사용자
- workspaces: 워크스페이스
- workspace_resources: 리소스 사용량
- audit_logs: 감사 로그
- infrastructure_servers: 인프라 서버
- server_credentials: 서버 인증 정보
- workspace_placements: 워크스페이스 배치
- placement_policies: 배치 정책
- user_sessions: 사용자 세션
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================================
    # 1. organizations 테이블
    # ============================================================
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('max_workspaces', sa.Integer(), default=100),
        sa.Column('max_users', sa.Integer(), default=500),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id'),
    )
    op.create_index('ix_organizations_org_id', 'organizations', ['org_id'])

    # ============================================================
    # 2. users 테이블
    # ============================================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('org_id', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255)),
        sa.Column('role', sa.String(50), nullable=False, default='developer'),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('email'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id']),
    )
    op.create_index('ix_users_user_id', 'users', ['user_id'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_org_id', 'users', ['org_id'])

    # ============================================================
    # 3. workspaces 테이블
    # ============================================================
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', sa.String(100), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', sa.String(100), nullable=False),
        sa.Column('org_id', sa.String(100)),
        sa.Column('container_id', sa.String(255)),
        sa.Column('status', sa.String(50), nullable=False, default='stopped'),
        sa.Column('root_path', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.user_id']),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id']),
    )
    op.create_index('ix_workspaces_workspace_id', 'workspaces', ['workspace_id'])
    op.create_index('ix_workspaces_owner_id', 'workspaces', ['owner_id'])
    op.create_index('ix_workspaces_org_id', 'workspaces', ['org_id'])
    op.create_index('ix_workspaces_status', 'workspaces', ['status'])
    # 최적화된 복합 인덱스
    op.create_index('idx_workspace_owner_status', 'workspaces', ['owner_id', 'status'])
    op.create_index('idx_workspace_org_status', 'workspaces', ['org_id', 'status'])
    op.create_index('idx_workspace_last_accessed_status', 'workspaces', ['status', 'last_accessed_at'])
    op.create_index('idx_workspace_owner_created', 'workspaces', ['owner_id', 'created_at'])

    # ============================================================
    # 4. workspace_resources 테이블
    # ============================================================
    op.create_table(
        'workspace_resources',
        sa.Column('workspace_id', sa.String(100), nullable=False),
        sa.Column('cpu_usage', sa.String(20)),
        sa.Column('memory_usage', sa.BigInteger()),
        sa.Column('disk_usage', sa.BigInteger()),
        sa.Column('network_io', sa.BigInteger()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('workspace_id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.workspace_id']),
    )

    # ============================================================
    # 5. audit_logs 테이블
    # ============================================================
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('workspace_id', sa.String(100), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('instruction_hash', sa.String(64)),
        sa.Column('response_hash', sa.String(64)),
        sa.Column('patch_hash', sa.String(64)),
        sa.Column('tokens_used', sa.Integer()),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.workspace_id']),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_workspace_id', 'audit_logs', ['workspace_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    # 최적화된 복합 인덱스
    op.create_index('idx_audit_user_time', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('idx_audit_workspace_time', 'audit_logs', ['workspace_id', 'timestamp'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])
    op.create_index('idx_audit_action_time', 'audit_logs', ['action', 'timestamp'])
    op.create_index('idx_audit_user_action', 'audit_logs', ['user_id', 'action'])

    # ============================================================
    # 6. infrastructure_servers 테이블
    # ============================================================
    op.create_table(
        'infrastructure_servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False, default=22),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('region', sa.String(100)),
        sa.Column('zone', sa.String(100)),
        sa.Column('status', sa.String(50), nullable=False, default='active'),
        sa.Column('max_workspaces', sa.Integer(), default=100),
        sa.Column('current_workspaces', sa.Integer(), default=0),
        sa.Column('cpu_capacity', sa.Numeric(10, 2)),
        sa.Column('memory_capacity', sa.BigInteger()),
        sa.Column('disk_capacity', sa.BigInteger()),
        sa.Column('cpu_usage', sa.Numeric(10, 2), default=0),
        sa.Column('memory_usage', sa.BigInteger(), default=0),
        sa.Column('disk_usage', sa.BigInteger(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('last_health_check', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('idx_server_status', 'infrastructure_servers', ['status'])
    op.create_index('idx_server_region', 'infrastructure_servers', ['region'])

    # ============================================================
    # 7. server_credentials 테이블
    # ============================================================
    op.create_table(
        'server_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('auth_type', sa.String(50), nullable=False),
        sa.Column('credential_name', sa.String(255), nullable=False),
        sa.Column('encrypted_private_key', sa.Text()),
        sa.Column('encrypted_certificate', sa.Text()),
        sa.Column('encrypted_api_key', sa.Text()),
        sa.Column('public_key', sa.Text()),
        sa.Column('key_fingerprint', sa.String(64)),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['server_id'], ['infrastructure_servers.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_credential_server_type', 'server_credentials', ['server_id', 'auth_type'])

    # ============================================================
    # 8. workspace_placements 테이블
    # ============================================================
    op.create_table(
        'workspace_placements',
        sa.Column('workspace_id', sa.String(100), nullable=False),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('container_id', sa.String(255)),
        sa.Column('placement_policy', sa.String(50)),
        sa.Column('placed_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('workspace_id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.workspace_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['server_id'], ['infrastructure_servers.id']),
    )
    op.create_index('ix_workspace_placements_server_id', 'workspace_placements', ['server_id'])

    # ============================================================
    # 9. placement_policies 테이블
    # ============================================================
    op.create_table(
        'placement_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('policy_type', sa.String(50), nullable=False),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('config', postgresql.JSONB()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    # ============================================================
    # 10. user_sessions 테이블
    # ============================================================
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(100), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_session_token', 'user_sessions', ['session_token'])
    op.create_index('idx_session_expires', 'user_sessions', ['expires_at'])


def downgrade() -> None:
    # 역순으로 테이블 삭제
    op.drop_table('user_sessions')
    op.drop_table('placement_policies')
    op.drop_table('workspace_placements')
    op.drop_table('server_credentials')
    op.drop_table('infrastructure_servers')
    op.drop_table('audit_logs')
    op.drop_table('workspace_resources')
    op.drop_table('workspaces')
    op.drop_table('users')
    op.drop_table('organizations')
