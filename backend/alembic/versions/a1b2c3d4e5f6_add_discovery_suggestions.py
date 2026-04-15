"""add discovery_suggestions table

Revision ID: a1b2c3d4e5f6
Revises: 639f7c41ec57
Create Date: 2026-04-15 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '639f7c41ec57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'discovery_suggestions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('symbol', sa.String(20), nullable=False, index=True),
        sa.Column('name', sa.String(255)),
        sa.Column('sector', sa.String(100)),
        sa.Column('discovery_score', sa.Float(), nullable=False),
        sa.Column('hedge_fund_score', sa.Float()),
        sa.Column('technical_score', sa.Float()),
        sa.Column('sector_score', sa.Float()),
        sa.Column('source', sa.String(50)),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('fund_count', sa.Integer()),
        sa.Column('fund_names', sa.JSON()),
        sa.Column('current_price', sa.Numeric(12, 4)),
        sa.Column('rsi_14', sa.Float()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('discovery_suggestions')
