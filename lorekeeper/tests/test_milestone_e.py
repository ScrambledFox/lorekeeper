"""
Tests for Milestone E: Mythic support polish.

This test suite validates that:
1. Documents have mode (STRICT/MYTHIC) and kind fields properly set
2. In-world author and in_world_date fields are returned in retrieval
3. Example mythic documents can be created and retrieved
4. Strict vs Mythic retrieval policies work correctly
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.db.models import Document, World


@pytest.mark.asyncio
async def test_mythic_document_creation(
    client: AsyncClient, test_world: World, db_session: AsyncSession
) -> None:
    """Test that mythic documents can be created with proper fields."""
    world_id = test_world.id

    # Create a mythic document
    response = await client.post(
        f"/worlds/{world_id}/documents",
        json={
            "mode": "MYTHIC",
            "kind": "SCRIPTURE",
            "title": "The Prophecy of the Three Moons",
            "author": "High Priestess Aella",
            "in_world_date": "Year -500 (Ancient Prophecy)",
            "text": "In the age when three moons align, a great shadow shall fall.",
            "provenance": {"source": "ancient_religious_text"},
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["mode"] == "MYTHIC"
    assert data["kind"] == "SCRIPTURE"
    assert data["title"] == "The Prophecy of the Three Moons"
    assert data["author"] == "High Priestess Aella"
    assert data["in_world_date"] == "Year -500 (Ancient Prophecy)"


@pytest.mark.asyncio
async def test_strict_document_creation(
    client: AsyncClient, test_world: World, db_session: AsyncSession
) -> None:
    """Test that strict documents can be created with proper fields."""
    world_id = test_world.id

    # Create a strict document
    response = await client.post(
        f"/worlds/{world_id}/documents",
        json={
            "mode": "STRICT",
            "kind": "CHRONICLE",
            "title": "Official Chronicle of Year 1050",
            "author": "Royal Historian",
            "in_world_date": "Year 1050",
            "text": "This year saw peace and prosperity in the realm.",
            "provenance": {"source": "official_records"},
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["mode"] == "STRICT"
    assert data["kind"] == "CHRONICLE"
    assert data["title"] == "Official Chronicle of Year 1050"
    assert data["author"] == "Royal Historian"
    assert data["in_world_date"] == "Year 1050"


@pytest.mark.asyncio
async def test_mythic_document_kinds(
    client: AsyncClient, test_world: World, db_session: AsyncSession
) -> None:
    """Test various mythic document kinds."""
    world_id = test_world.id

    kinds = [
        ("RUMOR", "Tavern Tales: The Duke Who Never Dies"),
        ("SCRIPTURE", "The Sacred Texts"),
        ("BALLAD", "The Ballad of Heroes"),
        ("PROPAGANDA", "The Glory of the Empire"),
        ("MEMOIR", "My Life in Exile"),
    ]

    for kind, title in kinds:
        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": kind,
                "title": title,
                "author": "Unknown",
                "in_world_date": "Year 1087",
                "text": f"This is a {kind.lower()} document.",
                "provenance": {"source": "test"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["kind"] == kind
        assert data["mode"] == "MYTHIC"


@pytest.mark.asyncio
async def test_retrieval_includes_provenance_fields(
    client: AsyncClient,
    test_world: World,
    test_document: Document,
) -> None:
    """Test that retrieval responses include all provenance fields."""
    world_id = test_world.id
    document_id = test_document.id

    # Index the document
    await client.post(f"/worlds/{world_id}/documents/{document_id}/index", json={})

    # Retrieve snippets
    response = await client.post(
        f"/worlds/{world_id}/retrieve",
        json={
            "query": "test",
            "policy": "HYBRID",
            "top_k": 5,
            "include_entities": False,
            "include_snippets": True,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify snippets include provenance fields
    if data["snippets"]:
        snippet = data["snippets"][0]
        assert "document_title" in snippet
        assert "document_kind" in snippet
        assert "document_mode" in snippet
        assert "document_author" in snippet
        assert "in_world_date" in snippet


@pytest.mark.asyncio
async def test_search_documents_by_mode(client: AsyncClient, test_world: World) -> None:
    """Test searching documents filtered by mode."""
    world_id = test_world.id

    # Create strict document
    response_strict = await client.post(
        f"/worlds/{world_id}/documents",
        json={
            "mode": "STRICT",
            "kind": "CHRONICLE",
            "title": "Official Records",
            "author": None,
            "in_world_date": None,
            "text": "Official truth",
            "provenance": None,
        },
    )
    assert response_strict.status_code == 201

    # Create mythic document
    response_mythic = await client.post(
        f"/worlds/{world_id}/documents",
        json={
            "mode": "MYTHIC",
            "kind": "RUMOR",
            "title": "Tavern Gossip",
            "author": "Unknown Drunk",
            "in_world_date": "Year 1087",
            "text": "Unverified tale",
            "provenance": None,
        },
    )
    assert response_mythic.status_code == 201

    # Search for STRICT only
    response_search_strict = await client.post(
        f"/worlds/{world_id}/documents/search?mode=STRICT",
        json={},
    )
    assert response_search_strict.status_code == 200
    data_strict = response_search_strict.json()
    assert all(doc["mode"] == "STRICT" for doc in data_strict["results"])

    # Search for MYTHIC only
    response_search_mythic = await client.post(
        f"/worlds/{world_id}/documents/search?mode=MYTHIC",
        json={},
    )
    assert response_search_mythic.status_code == 200
    data_mythic = response_search_mythic.json()
    assert all(doc["mode"] == "MYTHIC" for doc in data_mythic["results"])


@pytest.mark.asyncio
async def test_search_documents_by_kind(client: AsyncClient, test_world: World) -> None:
    """Test searching documents filtered by kind."""
    world_id = test_world.id

    # Create documents with different kinds
    kinds = ["SCRIPTURE", "RUMOR", "CHRONICLE"]
    for kind in kinds:
        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": kind,
                "title": f"Document of kind {kind}",
                "author": None,
                "in_world_date": None,
                "text": "Content",
                "provenance": None,
            },
        )
        assert response.status_code == 201

    # Search for specific kind
    response_search = await client.post(
        f"/worlds/{world_id}/documents/search?kind=SCRIPTURE",
        json={},
    )
    assert response_search.status_code == 200
    data = response_search.json()
    assert all(doc["kind"] == "SCRIPTURE" for doc in data["results"])


@pytest.mark.asyncio
async def test_mythic_document_with_in_world_date(client: AsyncClient, test_world: World) -> None:
    """Test that in-world dates are properly stored and retrieved."""
    world_id = test_world.id

    in_world_dates = [
        "Year -500 (Ancient Prophecy)",
        "Year 1050",
        "3rd Age, Spring Equinox",
        "The Time Before Memory",
    ]

    for in_world_date in in_world_dates:
        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "CHRONICLE",
                "title": f"Document from {in_world_date}",
                "author": "Scribe",
                "in_world_date": in_world_date,
                "text": "Content",
                "provenance": None,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["in_world_date"] == in_world_date


@pytest.mark.asyncio
async def test_strict_vs_mythic_retrieval_policy(client: AsyncClient, test_world: World) -> None:
    """Test that STRICT_ONLY, MYTHIC_ONLY, and HYBRID policies work correctly."""
    world_id = test_world.id

    # Create strict document
    response_strict = await client.post(
        f"/worlds/{world_id}/documents",
        json={
            "mode": "STRICT",
            "kind": "CHRONICLE",
            "title": "Strict Historical Record",
            "author": None,
            "in_world_date": None,
            "text": "This is historical fact about kings and battles.",
            "provenance": None,
        },
    )
    strict_doc_id = response_strict.json()["id"]

    # Create mythic document
    response_mythic = await client.post(
        f"/worlds/{world_id}/documents",
        json={
            "mode": "MYTHIC",
            "kind": "RUMOR",
            "title": "Legendary Tale",
            "author": "Storyteller",
            "in_world_date": "Year 1087",
            "text": "According to legend, a great hero once walked these lands.",
            "provenance": None,
        },
    )
    mythic_doc_id = response_mythic.json()["id"]

    # Index both documents
    await client.post(f"/worlds/{world_id}/documents/{strict_doc_id}/index", json={})
    await client.post(f"/worlds/{world_id}/documents/{mythic_doc_id}/index", json={})

    # Test STRICT_ONLY
    response_strict_policy = await client.post(
        f"/worlds/{world_id}/retrieve",
        json={
            "query": "historical",
            "policy": "STRICT_ONLY",
            "top_k": 5,
            "include_entities": False,
            "include_snippets": True,
        },
    )
    assert response_strict_policy.status_code == 200
    data_strict = response_strict_policy.json()
    # All snippets should be from STRICT documents
    for snippet in data_strict["snippets"]:
        assert snippet["document_mode"] == "STRICT"

    # Test MYTHIC_ONLY
    response_mythic_policy = await client.post(
        f"/worlds/{world_id}/retrieve",
        json={
            "query": "legend",
            "policy": "MYTHIC_ONLY",
            "top_k": 5,
            "include_entities": False,
            "include_snippets": True,
        },
    )
    assert response_mythic_policy.status_code == 200
    data_mythic = response_mythic_policy.json()
    # All snippets should be from MYTHIC documents
    for snippet in data_mythic["snippets"]:
        assert snippet["document_mode"] == "MYTHIC"
