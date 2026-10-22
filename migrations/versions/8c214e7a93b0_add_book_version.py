"""Add the book version counter without changing existing text columns.

Revision ID: 8c214e7a93b0
Revises: 46da991b1999
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "8c214e7a93b0"
down_revision: str | Sequence[str] | None = "46da991b1999"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Refuse incompatible existing data; never truncate titles or authors automatically.
    # Offline SQL generation cannot inspect rows; run the documented preflight separately.
    if not context.is_offline_mode():
        invalid_count = op.get_bind().scalar(
            sa.text(
                "SELECT COUNT(*) FROM books WHERE CHAR_LENGTH(title) > 100 "
                "OR CHAR_LENGTH(author) > 80"
            )
        )
        if invalid_count:
            raise RuntimeError(
                "Existing books exceed the new title (100) or author (80) limits. "
                "Review and correct those records before retrying the migration."
            )
    op.add_column(
        "books", sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("books", "version")
