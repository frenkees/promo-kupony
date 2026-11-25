"""Počáteční schéma: enumy + 4 tabulky

Revision ID: 0001
Revises:
Create Date: 2026-06-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

account_role = postgresql.ENUM(
    "operator",
    "manager",
    "master",
    name="account_role",
    create_type=False,
)
coupon_state = postgresql.ENUM(
    "VOLNA",
    "K_UPLATNENI",
    "VYRAZENA",
    name="coupon_state",
    create_type=False,
)
log_action = postgresql.ENUM(
    "VYDANI",
    "UPLATNENI",
    "VYRAZENI",
    "IMPORT",
    name="log_action",
    create_type=False,
)
log_result = postgresql.ENUM(
    "OK",
    "ODMITNUTO",
    "BYPASS",
    name="log_result",
    create_type=False,
)


def create_enum_type(name: str, values: Sequence[str]) -> None:
    values_sql = ", ".join(f"'{value}'" for value in values)
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
                CREATE TYPE {name} AS ENUM ({values_sql});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )


def upgrade() -> None:
    # --- PostgreSQL enum typy ---
    create_enum_type("account_role", ("operator", "manager", "master"))
    create_enum_type("coupon_state", ("VOLNA", "K_UPLATNENI", "VYRAZENA"))
    create_enum_type("log_action", ("VYDANI", "UPLATNENI", "VYRAZENI", "IMPORT"))
    create_enum_type("log_result", ("OK", "ODMITNUTO", "BYPASS"))

    # --- Tabulky ---
    op.create_table(
        "restaurants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("login", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role",
            account_role,
            nullable=False,
        ),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("baseline_user_agent", sa.Text(), nullable=True),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("login"),
    )

    op.create_table(
        "coupons",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column(
            "state",
            coupon_state,
            server_default="VOLNA",
            nullable=False,
        ),
        sa.Column("retired_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("code"),
    )

    op.create_table(
        "coupon_logs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("coupon_code", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column(
            "action",
            log_action,
            nullable=False,
        ),
        sa.Column(
            "result",
            log_result,
            nullable=False,
        ),
        sa.Column(
            "is_suspicious",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("suspicious_reason", sa.Text(), nullable=True),
        sa.Column(
            "server_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- Indexy na coupon_logs ---
    op.create_index("ix_coupon_logs_coupon_code", "coupon_logs", ["coupon_code"])
    op.create_index("ix_coupon_logs_is_suspicious", "coupon_logs", ["is_suspicious"])
    op.create_index("ix_coupon_logs_server_time", "coupon_logs", ["server_time"])


def downgrade() -> None:
    op.drop_index("ix_coupon_logs_server_time", table_name="coupon_logs")
    op.drop_index("ix_coupon_logs_is_suspicious", table_name="coupon_logs")
    op.drop_index("ix_coupon_logs_coupon_code", table_name="coupon_logs")
    op.drop_table("coupon_logs")
    op.drop_table("coupons")
    op.drop_table("accounts")
    op.drop_table("restaurants")
    op.execute("DROP TYPE IF EXISTS log_result")
    op.execute("DROP TYPE IF EXISTS log_action")
    op.execute("DROP TYPE IF EXISTS coupon_state")
    op.execute("DROP TYPE IF EXISTS account_role")
