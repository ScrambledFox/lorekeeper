"""
Pytest configuration and shared fixtures for integration tests.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lorekeeper.db.database import Base, get_async_session
from lorekeeper.main import app
from lorekeeper.models.domain import Document, DocumentSnippet, Entity, World

# Test database URL
TEST_DATABASE_URL = (
    "postgresql+asyncpg://lorekeeper:lorekeeper_dev_password@localhost/lorekeeper_test"
)


@pytest_asyncio.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine (function-scoped to work with pytest-asyncio)."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=False,
        pool_recycle=3600,
        pool_size=5,
        max_overflow=10,
    )

    # Create all tables
    async with engine.begin() as conn:
        try:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
        except Exception:
            pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with automatic rollback."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session
        if session.is_active:
            await session.rollback()


@pytest.fixture
def override_get_session(db_session: AsyncSession):
    """Override the get_async_session dependency for API testing."""

    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = _override
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(override_get_session: bool) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden session dependency."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest_asyncio.fixture
async def test_world(db_session: AsyncSession) -> World:
    """Create a test world for each test."""
    world = World(
        name="TestWorld",
        description="A test world",
    )
    db_session.add(world)
    await db_session.flush()
    await db_session.refresh(world)
    return world


@pytest_asyncio.fixture
async def test_entity(db_session: AsyncSession, test_world: World) -> Entity:
    """Create a test entity for each test."""
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
    await db_session.flush()
    await db_session.refresh(entity)
    return entity


@pytest_asyncio.fixture
async def test_document(db_session: AsyncSession, test_world: World) -> Document:
    """Create a test document for each test."""
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
    await db_session.flush()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def test_document_snippet(
    db_session: AsyncSession, test_world: World, test_document: Document
) -> DocumentSnippet:
    """Create a test document snippet for each test."""
    snippet = DocumentSnippet(
        document_id=test_document.id,
        world_id=test_world.id,
        snippet_index=0,
        start_char=0,
        end_char=50,
        snippet_text="This is a test document with content.",
        embedding=[0.1] * 1536,
    )
    db_session.add(snippet)
    await db_session.flush()
    await db_session.refresh(snippet)
    return snippet
