"""Initial schema with world, entity, document, and document_snippet tables.

Revision ID: 001
Revises:
Create Date: 2025-01-08 17:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create world table
    op.create_table(
        "world",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_world_id"), "world", ["id"], unique=False)

    # Create entity table
    op.create_table(
        "entity",
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
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("canonical_name", sa.String(255), nullable=False),
        sa.Column("aliases", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("summary", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["world_id"], ["world.id"]),
    )
    op.create_index(op.f("ix_entity_id"), "entity", ["id"], unique=False)
    op.create_index(op.f("ix_entity_world_id"), "entity", ["world_id"], unique=False)

    # Create document table
    op.create_table(
        "document",
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
        sa.Column("mode", sa.String(50), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("in_world_date", sa.String(255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("provenance", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["world_id"], ["world.id"]),
    )
    op.create_index(op.f("ix_document_id"), "document", ["id"], unique=False)
    op.create_index(op.f("ix_document_world_id"), "document", ["world_id"], unique=False)
    op.create_index(op.f("ix_document_mode"), "document", ["mode"], unique=False)

    # Create document_snippet table with vector column
    # Using raw SQL to create vector column
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "document_snippet",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "world_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("snippet_index", sa.Integer(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("snippet_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"]),
        sa.ForeignKeyConstraint(["world_id"], ["world.id"]),
    )
    # Add vector column separately to ensure extension is available
    op.execute("ALTER TABLE document_snippet ADD COLUMN embedding vector(1536) NULL")

    op.create_index(op.f("ix_document_snippet_id"), "document_snippet", ["id"], unique=False)
    op.create_index(
        op.f("ix_document_snippet_document_id"), "document_snippet", ["document_id"], unique=False
    )
    op.create_index(
        op.f("ix_document_snippet_world_id"), "document_snippet", ["world_id"], unique=False
    )
    # Create index for vector similarity search
    op.execute(
        "CREATE INDEX ON document_snippet USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )

    # Create entity_mention table
    op.create_table(
        "entity_mention",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "snippet_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("mention_text", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["snippet_id"], ["document_snippet.id"]),
        sa.ForeignKeyConstraint(["entity_id"], ["entity.id"]),
    )
    op.create_index(op.f("ix_entity_mention_id"), "entity_mention", ["id"], unique=False)
    op.create_index(
        op.f("ix_entity_mention_snippet_id"), "entity_mention", ["snippet_id"], unique=False
    )
    op.create_index(
        op.f("ix_entity_mention_entity_id"), "entity_mention", ["entity_id"], unique=False
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f("ix_entity_mention_entity_id"), table_name="entity_mention")
    op.drop_index(op.f("ix_entity_mention_snippet_id"), table_name="entity_mention")
    op.drop_index(op.f("ix_entity_mention_id"), table_name="entity_mention")
    op.drop_table("entity_mention")

    op.drop_index("ix_document_snippet_embedding", table_name="document_snippet")
    op.drop_index(op.f("ix_document_snippet_world_id"), table_name="document_snippet")
    op.drop_index(op.f("ix_document_snippet_document_id"), table_name="document_snippet")
    op.drop_index(op.f("ix_document_snippet_id"), table_name="document_snippet")
    op.drop_table("document_snippet")

    op.drop_index(op.f("ix_document_mode"), table_name="document")
    op.drop_index(op.f("ix_document_world_id"), table_name="document")
    op.drop_index(op.f("ix_document_id"), table_name="document")
    op.drop_table("document")

    op.drop_index(op.f("ix_entity_world_id"), table_name="entity")
    op.drop_index(op.f("ix_entity_id"), table_name="entity")
    op.drop_table("entity")

    op.drop_index(op.f("ix_world_id"), table_name="world")
    op.drop_table("world")
