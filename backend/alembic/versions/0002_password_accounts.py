"""password accounts

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.Text(), nullable=True))
    # Partial, so rows seen via platform tokens (no password) can never block or collide.
    op.create_index(
        "uq_users_lower_email_password",
        "users",
        [sa.literal_column("lower(email)")],
        unique=True,
        postgresql_where=sa.text("password_hash is not null"),
    )


def downgrade() -> None:
    op.drop_index("uq_users_lower_email_password", table_name="users")
    op.drop_column("users", "password_hash")
