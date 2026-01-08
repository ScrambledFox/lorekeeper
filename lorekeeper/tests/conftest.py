"""
Pytest configuration and shared fixtures for integration tests.
"""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lorekeeper.api.main import app
from lorekeeper.db.database import Base, get_async_session
from lorekeeper.db.models import Document, DocumentSnippet, Entity, World

# Test database URL
TEST_DATABASE_URL = (
    "postgresql+asyncpg://lorekeeper:lorekeeper_dev_password@localhost/lorekeeper_test"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        # Try to create extensions if not exist
        try:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
        except Exception:
            pass  # Extensions might already exist

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

        # Cleanup after each test
        await session.execute(text("DELETE FROM entity_mention"))
        await session.execute(text("DELETE FROM document_snippet"))
        await session.execute(text("DELETE FROM document"))
        await session.execute(text("DELETE FROM entity"))
        await session.execute(text("DELETE FROM world"))
        await session.commit()


@pytest.fixture
def override_get_session(db_session: AsyncSession):
    """Override the get_async_session dependency."""

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_world(db_session: AsyncSession) -> World:
    """Create a test world."""
    world = World(
        name="TestWorld",
        description="A test world",
    )
    db_session.add(world)
    await db_session.commit()
    await db_session.refresh(world)
    return world


@pytest.fixture
async def test_entity(db_session: AsyncSession, test_world: World) -> Entity:
    """Create a test entity."""
    entity = Entity(
        world_id=test_world.id,
        type="Character",
        canonical_name="TestHero",
        aliases=["Hero"],
        summary="A test character",
        description="A longer description of the test character",
        tags=["warrior", "brave"],
    )
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)
    return entity


@pytest.fixture
async def test_document(db_session: AsyncSession, test_world: World) -> Document:
    """Create a test document."""
    doc = Document(
        world_id=test_world.id,
        mode="STRICT",
        kind="CHRONICLE",
        title="Test Document",
        author="Test Author",
        in_world_date="Year 1000",
        text="This is a test document with content. It has multiple sentences. The document contains useful information.",
        provenance={"source": "test"},
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.fixture
async def test_document_snippet(
    db_session: AsyncSession, test_world: World, test_document: Document
) -> DocumentSnippet:
    """Create a test document snippet."""
    snippet = DocumentSnippet(
        document_id=test_document.id,
        world_id=test_world.id,
        snippet_index=0,
        start_char=0,
        end_char=50,
        snippet_text="This is a test document with content.",
        embedding=[0.1] * 1536,  # Mock embedding
    )
    db_session.add(snippet)
    await db_session.commit()
    await db_session.refresh(snippet)
    return snippet
