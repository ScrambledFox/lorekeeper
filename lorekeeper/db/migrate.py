#!/usr/bin/env python3
"""
Standalone migration runner for LoreKeeper.
Runs migrations without importing the complex database.py module.
"""

import psycopg
import sys
from pathlib import Path

# Database connection string
DATABASE_URL = "postgresql://lorekeeper:lorekeeper_dev_password@localhost:5432/lorekeeper"


def get_migration_sql() -> str:
    """Get the initial migration SQL."""
    return """
BEGIN;

-- Create world table
CREATE TABLE IF NOT EXISTS world (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_world_id ON world(id);

-- Create entity table
CREATE TABLE IF NOT EXISTS entity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    world_id UUID NOT NULL REFERENCES world(id),
    type VARCHAR(100) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,
    aliases TEXT[] NOT NULL DEFAULT '{}',
    summary VARCHAR(500),
    description TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_entity_id ON entity(id);
CREATE INDEX IF NOT EXISTS ix_entity_world_id ON entity(world_id);

-- Create document table
CREATE TABLE IF NOT EXISTS document (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    world_id UUID NOT NULL REFERENCES world(id),
    mode VARCHAR(50) NOT NULL,
    kind VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255),
    in_world_date VARCHAR(255),
    text TEXT NOT NULL,
    provenance JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_document_id ON document(id);
CREATE INDEX IF NOT EXISTS ix_document_world_id ON document(world_id);
CREATE INDEX IF NOT EXISTS ix_document_mode ON document(mode);

-- Create document_snippet table
CREATE TABLE IF NOT EXISTS document_snippet (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES document(id),
    world_id UUID NOT NULL REFERENCES world(id),
    snippet_index INTEGER NOT NULL,
    start_char INTEGER NOT NULL,
    end_char INTEGER NOT NULL,
    snippet_text TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_document_snippet_id ON document_snippet(id);
CREATE INDEX IF NOT EXISTS ix_document_snippet_document_id ON document_snippet(document_id);
CREATE INDEX IF NOT EXISTS ix_document_snippet_world_id ON document_snippet(world_id);
CREATE INDEX IF NOT EXISTS ix_document_snippet_embedding ON document_snippet USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create entity_mention table
CREATE TABLE IF NOT EXISTS entity_mention (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snippet_id UUID NOT NULL REFERENCES document_snippet(id),
    entity_id UUID NOT NULL REFERENCES entity(id),
    mention_text VARCHAR(255) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_entity_mention_id ON entity_mention(id);
CREATE INDEX IF NOT EXISTS ix_entity_mention_snippet_id ON entity_mention(snippet_id);
CREATE INDEX IF NOT EXISTS ix_entity_mention_entity_id ON entity_mention(entity_id);

COMMIT;
"""


def run_migrations() -> None:
    """Run all migrations."""
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
            conn.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

            sql = get_migration_sql()
            conn.execute(sql)

            print("✓ Database migrations completed successfully")

    except Exception as e:
        print(f"✗ Migration failed: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    run_migrations()
