"""Add belief_prevalence column to claim table.

Revision ID: 004
Revises: 003
Create Date: 2025-01-09 10:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add belief_prevalence column to claim table
    op.add_column(
        "claim",
        sa.Column(
            "belief_prevalence",
            sa.Float(),
            nullable=False,
            server_default="0.5",
        ),
    )


def downgrade() -> None:
    # Remove belief_prevalence column from claim table
    op.drop_column("claim", "belief_prevalence")
