"""Initial schema — exchanges, trading_pairs, candles, screener_rules, alerts.

Revision ID: 7e8fbe497dc0
Revises:
Create Date: 2026-03-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7e8fbe497dc0"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # exchanges                                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "exchanges",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("slug", sa.String(32), nullable=False),
        sa.UniqueConstraint("slug", name="uq_exchanges_slug"),
    )

    # ------------------------------------------------------------------ #
    # trading_pairs                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "trading_pairs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("exchange_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["exchange_id"], ["exchanges.id"], name="fk_trading_pairs_exchange"),
        sa.UniqueConstraint("exchange_id", "symbol", "timeframe", name="uq_trading_pairs_exchange_symbol_timeframe"),
    )
    op.create_index("ix_trading_pairs_active", "trading_pairs", ["active"])

    # ------------------------------------------------------------------ #
    # screener_rules                                                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "screener_rules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # ------------------------------------------------------------------ #
    # candles                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "candles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("pair_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["pair_id"], ["trading_pairs.id"], name="fk_candles_pair"),
        sa.UniqueConstraint("pair_id", "timestamp", name="uq_candles_pair_timestamp"),
    )
    op.create_index("ix_candles_pair_timestamp", "candles", ["pair_id", sa.text("timestamp DESC")])

    # ------------------------------------------------------------------ #
    # alerts                                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("pair_id", sa.Integer(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["rule_id"], ["screener_rules.id"], name="fk_alerts_rule"),
        sa.ForeignKeyConstraint(["pair_id"], ["trading_pairs.id"], name="fk_alerts_pair"),
    )
    op.create_index("ix_alerts_rule_pair_triggered_at", "alerts", ["rule_id", "pair_id", "triggered_at"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("candles")
    op.drop_table("screener_rules")
    op.drop_table("trading_pairs")
    op.drop_table("exchanges")
