"""add dedup_hours to screener_rules

Revision ID: f011f5741b77
Revises: a4f9b2c1d3e0
Create Date: 2026-03-31 18:37:49.935859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f011f5741b77'
down_revision: Union[str, None] = 'a4f9b2c1d3e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'screener_rules',
        sa.Column('dedup_hours', sa.Integer(), nullable=False, server_default='4'),
    )


def downgrade() -> None:
    op.drop_column('screener_rules', 'dedup_hours')
