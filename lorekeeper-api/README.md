# LoreKeeper API
FastAPI backend for managing generated worlds, lore, retrieval, and multimodal assets (video/audio/image/map/PDF). Provides CRUD for worlds/entities/claims/books/sources plus an asset registry with idempotent job tracking and S3-style storage integration.

## Running Locally (uv + just)
- Prereqs: Python 3.11, [uv](https://github.com/astral-sh/uv), Docker (for Postgres/S3-compatible storage if you want it locally), `just`.
- Install deps into the repo’s shared venv: `just setup`
- Start Postgres only: `just db-up` (uses `docker-compose.yml`; defaults to port 5432)
- Apply migrations: `just db-upgrade`
- Run the API with reload: `just dev` (served at `http://localhost:8000`; docs at `/docs` and `/redoc`)

## Running with Docker Compose
- From `lorekeeper-api/`: `docker-compose up --build`
- API exposed on `http://localhost:8000`, Postgres on `localhost:5432` with user/db/password `lorekeeper`.

## Configuration
Environment variables (see `app/core/config.py` for defaults):
- `DATABASE_URL` / `TEST_DATABASE_URL`
- `ENVIRONMENT` (`development`/`production`), `DEBUG`
- OpenAI: `OPENAI_API_KEY`, `OPENAI_ORGANIZATION`, `OPENAI_EMBEDDING_MODEL_ID`, `OPENAI_EMBEDDING_DIMENSIONS`
- S3/object storage: `S3_BUCKET_NAME`, `S3_REGION`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT_URL`, `S3_PRESIGNED_URL_EXPIRY_SECONDS`
- Pagination: `DEFAULT_PAGE_SIZE`, `MAX_PAGE_SIZE`

## Core Endpoints
- Health/info: `/`, `/info`, `/health`
- Worlds: `/worlds`
- Entities: `/entities`
- Claims (searchable): `/claims`
- Books & sources: `/books`, `/sources`
- Assets (see below): `/assets/*`
All endpoints return OpenAPI docs at `/docs` once the server is running.

## Asset & Job Workflow
- Create an asset job (idempotent on canonicalized input): `POST /assets/asset-jobs` with `world_id`, `asset_type`, `provider`, `prompt_spec`, and lore references (`claim_ids`, `entity_ids`, `source_chunk_ids`, `source_id`).
- Worker updates status: `PATCH /assets/asset-jobs/{id}` (requires `Authorization: Bearer <token>`; token presence is validated today).
- Worker completes with asset payload: `POST /assets/asset-jobs/{id}/complete` → creates Asset, links derivation, sets job `SUCCEEDED`.
- Worker failure path: `POST /assets/asset-jobs/{id}/fail`.
- Retrieve assets/jobs and filter by world/type/status or related lore IDs: `GET /assets/assets`, `GET /assets/asset-jobs`.
- Presigned URLs: `POST /assets/assets/{asset_id}/presign-download` and `POST /assets/assets/presign-upload`.
Implementation details and schema are documented in `docs/IMPLEMENTATION.md`.

## Testing
- Run suite: `just test` (or `just test-v` / `just test-cov`)
- E2E asset workflow (expects API + Postgres running at localhost:8000): `cd lorekeeper-api && uv run tests/e2e_test_assets.py`

## Project Layout
- `app/main.py` – FastAPI app/bootstrap
- `app/routes/` – routers for worlds, entities, claims, books, sources, assets
- `app/models/api/` & `app/models/db/` – Pydantic schemas and SQLAlchemy models
- `app/repositories/` – DB accessors; `app/utils/` – validation, hashing, S3 helpers
- `app/db/migrations/` – Alembic environment and migration versions
- `docs/` – implementation notes and diagrams (e.g., `docs/IMPLEMENTATION.md`)
