"""add portfolio_holdings

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-16 08:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'portfolio_holdings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('shares', sa.Numeric(14, 4), nullable=False),
        sa.Column('entry_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('notes', sa.Text()),
        sa.Column('last_action', sa.String(30)),
        sa.Column('last_check_at', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('portfolio_holdings')
