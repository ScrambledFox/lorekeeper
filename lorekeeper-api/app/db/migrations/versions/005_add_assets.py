"""Add Asset, AssetJob, and AssetDerivation tables for multimodal assets support.

Revision ID: 005
Revises: 004
Create Date: 2025-01-17 18:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create asset table
    op.create_table(
        "asset",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("format", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="READY"),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_asset_world_id", "asset", ["world_id"])
    op.create_index("ix_asset_type", "asset", ["type"])
    op.create_index(
        "ix_asset_created_at", "asset", ["created_at"], postgresql_order_by="created_at DESC"
    )

    # Create asset_job table
    op.create_table(
        "asset_job",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="QUEUED"),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("prompt_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_job_world_id", "asset_job", ["world_id"])
    op.create_index("ix_asset_job_status", "asset_job", ["status"])
    op.create_index("ix_asset_job_input_hash", "asset_job", ["input_hash"])
    op.create_index(
        "ix_asset_job_created_at",
        "asset_job",
        ["created_at"],
        postgresql_order_by="created_at DESC",
    )

    # Create asset_derivation table
    op.create_table(
        "asset_derivation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("lore_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["asset.id"]),
        sa.ForeignKeyConstraint(["asset_job_id"], ["asset_job.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_job_id"),
    )
    op.create_index("ix_asset_derivation_world_id", "asset_derivation", ["world_id"])
    op.create_index("ix_asset_derivation_asset_job_id", "asset_derivation", ["asset_job_id"])
    op.create_index("ix_asset_derivation_input_hash", "asset_derivation", ["input_hash"])

    # Create asset_derivation_claim join table
    op.create_table(
        "asset_derivation_claim",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("derivation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["derivation_id"], ["asset_derivation.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_asset_derivation_claim_derivation_id", "asset_derivation_claim", ["derivation_id"]
    )
    op.create_index("ix_asset_derivation_claim_claim_id", "asset_derivation_claim", ["claim_id"])

    # Create asset_derivation_entity join table
    op.create_table(
        "asset_derivation_entity",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("derivation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["derivation_id"], ["asset_derivation.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_asset_derivation_entity_derivation_id", "asset_derivation_entity", ["derivation_id"]
    )
    op.create_index(
        "ix_asset_derivation_entity_entity_id", "asset_derivation_entity", ["entity_id"]
    )

    # Create asset_derivation_source_chunk join table
    op.create_table(
        "asset_derivation_source_chunk",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("derivation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["derivation_id"], ["asset_derivation.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_asset_derivation_source_chunk_derivation_id",
        "asset_derivation_source_chunk",
        ["derivation_id"],
    )
    op.create_index(
        "ix_asset_derivation_source_chunk_source_chunk_id",
        "asset_derivation_source_chunk",
        ["source_chunk_id"],
    )


def downgrade() -> None:
    # Drop all indices and tables in reverse order
    op.drop_index(
        "ix_asset_derivation_source_chunk_source_chunk_id",
        table_name="asset_derivation_source_chunk",
    )
    op.drop_index(
        "ix_asset_derivation_source_chunk_derivation_id", table_name="asset_derivation_source_chunk"
    )
    op.drop_table("asset_derivation_source_chunk")

    op.drop_index("ix_asset_derivation_entity_entity_id", table_name="asset_derivation_entity")
    op.drop_index("ix_asset_derivation_entity_derivation_id", table_name="asset_derivation_entity")
    op.drop_table("asset_derivation_entity")

    op.drop_index("ix_asset_derivation_claim_claim_id", table_name="asset_derivation_claim")
    op.drop_index("ix_asset_derivation_claim_derivation_id", table_name="asset_derivation_claim")
    op.drop_table("asset_derivation_claim")

    op.drop_index("ix_asset_derivation_input_hash", table_name="asset_derivation")
    op.drop_index("ix_asset_derivation_asset_job_id", table_name="asset_derivation")
    op.drop_index("ix_asset_derivation_world_id", table_name="asset_derivation")
    op.drop_table("asset_derivation")

    op.drop_index("ix_asset_job_created_at", table_name="asset_job")
    op.drop_index("ix_asset_job_input_hash", table_name="asset_job")
    op.drop_index("ix_asset_job_status", table_name="asset_job")
    op.drop_index("ix_asset_job_world_id", table_name="asset_job")
    op.drop_table("asset_job")

    op.drop_index("ix_asset_created_at", table_name="asset")
    op.drop_index("ix_asset_type", table_name="asset")
    op.drop_index("ix_asset_world_id", table_name="asset")
    op.drop_table("asset")
