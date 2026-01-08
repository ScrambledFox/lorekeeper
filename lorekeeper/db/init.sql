-- Enable pgvector extension
-- Note: pgvector may not be available in Alpine Linux
-- If you need it, use the pgvector/pgvector image instead
-- For now, we'll attempt to create it but won't fail if it's not available

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Try to enable pgvector if available
-- Comment this out if using standard postgres:16-alpine
-- CREATE EXTENSION IF NOT EXISTS vector;

COMMENT ON SCHEMA public IS 'LoreKeeper database schema';

