from __future__ import annotations

from alembic import op
import sqlalchemy as sa

"""
create plans and subscriptions

Revision ID: 53f1a2c8b7d1
Revises: 52c269307fec
Create Date: 2026-01-03
"""

# revision identifiers, used by Alembic.
revision = "53f1a2c8b7d1"
down_revision = "52c269307fec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- plans ---
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),

        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),

        sa.Column("max_servers", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_devices", sa.Integer(), nullable=False, server_default="1"),

        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ux_plans_code", "plans", ["code"], unique=True)

    # --- subscriptions ---
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),

        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),

        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('active','canceled','trial')", name="ck_subscriptions_status"),
    )

    op.create_index("ux_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"], unique=False)

    # --- seed plans ---
    op.execute(
        """
        INSERT INTO plans (code, name, price_cents, currency, max_servers, max_devices, is_active)
        VALUES
            ('free',  'Free',  0,    'USD', 1, 1, true),
            ('basic', 'Basic', 990,  'USD', 3, 5, true),
            ('pro',   'Pro',   1990, 'USD', 10, 50, true)
        ON CONFLICT (code) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ux_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ux_plans_code", table_name="plans")
    op.drop_table("plans")
