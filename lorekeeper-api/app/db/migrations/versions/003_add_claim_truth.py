"""Add claim and snippet_analysis tables for Phase 2 ClaimTruth system.

Revision ID: 003
Revises: 002
Create Date: 2025-01-09 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create claim table
    op.create_table(
        "claim",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "world_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "snippet_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "claimed_by_entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "subject_entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "predicate",
            sa.String(255),
            nullable=False,
        ),
        sa.Column(
            "object_text",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "object_entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "truth_status",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "canon_ref_entity_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["world_id"], ["world.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snippet_id"], ["document_snippet.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claimed_by_entity_id"], ["entity.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_entity_id"], ["entity.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["object_entity_id"], ["entity.id"], ondelete="SET NULL"),
    )

    # Create indexes for claim table
    op.create_index("idx_claim_world_id", "claim", ["world_id"])
    op.create_index("idx_claim_subject_entity_id", "claim", ["subject_entity_id"])
    op.create_index("idx_claim_object_entity_id", "claim", ["object_entity_id"])
    op.create_index("idx_claim_truth_status", "claim", ["truth_status"])
    op.create_index("idx_claim_snippet_id", "claim", ["snippet_id"])
    op.create_index("idx_claim_predicate", "claim", ["predicate"])

    # Create snippet_analysis table
    op.create_table(
        "snippet_analysis",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "world_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "snippet_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "contradiction_score",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "contains_claim_about_canon_entities",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "analysis_notes",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "analyzed_by",
            sa.String(50),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["world_id"], ["world.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["snippet_id"], ["document_snippet.id"], ondelete="CASCADE"),
    )

    # Create indexes for snippet_analysis table
    op.create_index("idx_snippet_analysis_snippet_id", "snippet_analysis", ["snippet_id"])
    op.create_index("idx_snippet_analysis_world_id", "snippet_analysis", ["world_id"])


def downgrade() -> None:
    # Drop snippet_analysis table
    op.drop_index("idx_snippet_analysis_world_id", table_name="snippet_analysis")
    op.drop_index("idx_snippet_analysis_snippet_id", table_name="snippet_analysis")
    op.drop_table("snippet_analysis")

    # Drop claim table
    op.drop_index("idx_claim_predicate", table_name="claim")
    op.drop_index("idx_claim_snippet_id", table_name="claim")
    op.drop_index("idx_claim_truth_status", table_name="claim")
    op.drop_index("idx_claim_object_entity_id", table_name="claim")
    op.drop_index("idx_claim_subject_entity_id", table_name="claim")
    op.drop_index("idx_claim_world_id", table_name="claim")
    op.drop_table("claim")
