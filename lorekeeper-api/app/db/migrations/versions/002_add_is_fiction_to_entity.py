"""Add is_fiction field to entity table to distinguish between fact and fiction entities.

Revision ID: 002
Revises: 001
Create Date: 2025-01-09 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add is_fiction boolean column to entity table."""
    op.add_column(
        "entity",
        sa.Column("is_fiction", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove is_fiction column from entity table."""
    op.drop_column("entity", "is_fiction")
