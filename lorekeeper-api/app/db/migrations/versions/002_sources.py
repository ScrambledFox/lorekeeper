"""Add source and source_chunk tables.

Revision ID: 002
Revises: 001
Create Date: 2026-01-17 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "source",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("world_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column("origin", sa.String(255), nullable=True),
        sa.Column("book_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["world_id"], ["world.id"]),
    )
    op.create_index(op.f("ix_source_id"), "source", ["id"], unique=False)
    op.create_index(op.f("ix_source_world_id"), "source", ["world_id"], unique=False)

    op.create_table(
        "source_chunk",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_id"], ["source.id"]),
    )
    op.execute("ALTER TABLE source_chunk ADD COLUMN embedding vector(1536) NOT NULL")

    op.create_index(op.f("ix_source_chunk_id"), "source_chunk", ["id"], unique=False)
    op.create_index(op.f("ix_source_chunk_source_id"), "source_chunk", ["source_id"], unique=False)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_source_chunk_embedding ON source_chunk "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_index("ix_source_chunk_embedding", table_name="source_chunk")
    op.drop_index(op.f("ix_source_chunk_source_id"), table_name="source_chunk")
    op.drop_index(op.f("ix_source_chunk_id"), table_name="source_chunk")
    op.drop_table("source_chunk")

    op.drop_index(op.f("ix_source_world_id"), table_name="source")
    op.drop_index(op.f("ix_source_id"), table_name="source")
    op.drop_table("source")
