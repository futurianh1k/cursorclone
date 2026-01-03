"""Add 2FA fields to users table

Revision ID: 0002
Revises: 0001
Create Date: 2026-01-03

2FA (Two-Factor Authentication) 지원을 위한 필드 추가:
- totp_enabled: 2FA 활성화 여부
- totp_secret: TOTP 시크릿 (암호화됨)
- totp_secret_pending: 설정 중인 시크릿
- backup_code_hashes: 백업 코드 해시 목록
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 2FA 관련 필드 추가
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), default=False, nullable=True))
    op.add_column('users', sa.Column('totp_secret', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('totp_secret_pending', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('backup_code_hashes', postgresql.JSONB(), nullable=True))
    op.add_column('users', sa.Column('backup_code_hashes_pending', postgresql.JSONB(), nullable=True))
    
    # 기본값 설정
    op.execute("UPDATE users SET totp_enabled = false WHERE totp_enabled IS NULL")
    
    # NOT NULL 제약 추가 (선택사항)
    # op.alter_column('users', 'totp_enabled', nullable=False)


def downgrade() -> None:
    op.drop_column('users', 'backup_code_hashes_pending')
    op.drop_column('users', 'backup_code_hashes')
    op.drop_column('users', 'totp_secret_pending')
    op.drop_column('users', 'totp_secret')
    op.drop_column('users', 'totp_enabled')
