"""Add users table and user_id FK to screener_rules and alerts.

Existing rows are backfilled to a seed admin user (id=1).
After backfill, user_id is made NOT NULL on both tables.

Revision ID: a4f9b2c1d3e0
Revises: 7e8fbe497dc0
Create Date: 2026-03-31 00:00:00.000000

"""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4f9b2c1d3e0"
down_revision: Union[str, None] = "7e8fbe497dc0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # users                                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("hashed_password", sa.String(128), nullable=False, server_default=""),
        sa.Column("telegram_chat_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # Seed the admin user so existing rows can reference it.
    op.execute(
        sa.text(
            "INSERT INTO users (id, email, hashed_password, telegram_chat_id, language, created_at) "
            "VALUES (1, 'admin@candle.local', '', '', 'en', :now)"
        ).bindparams(now=datetime.now(tz=timezone.utc))
    )

    # ------------------------------------------------------------------ #
    # screener_rules — add nullable user_id, backfill, then NOT NULL      #
    # ------------------------------------------------------------------ #
    op.add_column(
        "screener_rules",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.execute(sa.text("UPDATE screener_rules SET user_id = 1"))
    op.alter_column("screener_rules", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_screener_rules_user",
        "screener_rules", "users",
        ["user_id"], ["id"],
    )

    # ------------------------------------------------------------------ #
    # alerts — add nullable user_id, backfill, then NOT NULL              #
    # ------------------------------------------------------------------ #
    op.add_column(
        "alerts",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.execute(sa.text("UPDATE alerts SET user_id = 1"))
    op.alter_column("alerts", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_alerts_user",
        "alerts", "users",
        ["user_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_alerts_user", "alerts", type_="foreignkey")
    op.drop_column("alerts", "user_id")

    op.drop_constraint("fk_screener_rules_user", "screener_rules", type_="foreignkey")
    op.drop_column("screener_rules", "user_id")

    op.drop_table("users")
