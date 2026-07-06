"""oauth accounts

Revision ID: 0002_oauth_accounts
Revises: 0001_saas_v1
Create Date: 2026-07-06
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_oauth_accounts"
down_revision = "0001_saas_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_subject", name="uq_oauth_provider_subject"),
    )
    op.create_index(op.f("ix_oauth_accounts_provider"), "oauth_accounts", ["provider"], unique=False)
    op.create_index(op.f("ix_oauth_accounts_user_id"), "oauth_accounts", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_oauth_accounts_user_id"), table_name="oauth_accounts")
    op.drop_index(op.f("ix_oauth_accounts_provider"), table_name="oauth_accounts")
    op.drop_table("oauth_accounts")
