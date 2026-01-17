"""
Integration tests for lore document indexing and embedding.

This module tests the indexing pipeline that converts narrative documents into
searchable snippets with embeddings for semantic retrieval.
"""

import pytest
from httpx import AsyncClient

from lorekeeper.models.domain import Document, World


class TestLoreDocumentStorage:
    """Test suite for storing narrative documents."""

    @pytest.mark.asyncio
    async def test_store_canonical_document(self, client: AsyncClient, test_world: World) -> None:
        """Test storing a canonical document for later retrieval."""
        response = await client.post(
            f"/worlds/{test_world.id}/documents",
            json={
                "mode": "STRICT",
                "kind": "CHRONICLE",
                "title": "Historical Record",
                "author": "Historian",
                "in_world_date": "Year 1000",
                "text": "This is a historical document with important information.",
                "provenance": {"source": "archive"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Historical Record"
        assert data["mode"] == "STRICT"
        assert data["kind"] == "CHRONICLE"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_store_mythic_narrative(self, client: AsyncClient, test_world: World) -> None:
        """Test storing a mythic narrative document."""
        response = await client.post(
            f"/worlds/{test_world.id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "RUMOR",
                "title": "A Tavern Tale",
                "author": "Storyteller",
                "text": "They say that once there was a great hero...",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["mode"] == "MYTHIC"
        assert data["kind"] == "RUMOR"

    @pytest.mark.asyncio
    async def test_retrieve_stored_document(
        self, client: AsyncClient, test_document: Document
    ) -> None:
        """Test retrieving a previously stored document."""
        response = await client.get(
            f"/worlds/{test_document.world_id}/documents/{test_document.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_document.id)
        assert data["title"] == test_document.title
        assert data["mode"] == test_document.mode

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_document(
        self, client: AsyncClient, test_world: World
    ) -> None:
        """Test that retrieving a non-existent document returns 404."""
        from uuid import uuid4

        response = await client.get(f"/worlds/{test_world.id}/documents/{uuid4()}")

        assert response.status_code == 404


class TestLoreIndexing:
    """Test suite for indexing and chunking documents for semantic search."""

    @pytest.mark.asyncio
    async def test_index_narrative_document(
        self, client: AsyncClient, test_document: Document
    ) -> None:
        """Test chunking and embedding a narrative document."""
        response = await client.post(
            f"/worlds/{test_document.world_id}/documents/{test_document.id}/index",
            json={
                "chunk_size_min": 300,
                "chunk_size_max": 800,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == str(test_document.id)
        # Should create at least one snippet
        assert data["snippets_created"] >= 1
        assert len(data["snippet_ids"]) >= 1


class TestNarrativeDiscovery:
    """Test suite for finding and filtering documents by metadata."""

    @pytest.mark.asyncio
    async def test_find_documents_by_title(
        self, client: AsyncClient, test_document: Document
    ) -> None:
        """Test finding documents by searching their title."""
        response = await client.post(
            f"/worlds/{test_document.world_id}/documents/search",
            json={"query": "Test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(doc["title"] == "Test Document" for doc in data["results"])

    @pytest.mark.asyncio
    async def test_filter_documents_by_lore_mode(
        self, client: AsyncClient, test_world: World
    ) -> None:
        """Test filtering documents by their lore mode (canonical vs mythic)."""
        # Create a MYTHIC document
        await client.post(
            f"/worlds/{test_world.id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "RUMOR",
                "title": "Myth",
                "text": "A mythical tale",
            },
        )

        response = await client.post(
            f"/worlds/{test_world.id}/documents/search",
            json={"mode": "MYTHIC"},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(doc["mode"] == "MYTHIC" for doc in data["results"])

    @pytest.mark.asyncio
    async def test_filter_documents_by_narrative_kind(
        self, client: AsyncClient, test_document: Document
    ) -> None:
        """Test filtering documents by their narrative kind."""
        response = await client.post(
            f"/worlds/{test_document.world_id}/documents/search",
            json={"kind": "CHRONICLE"},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(doc["kind"] == "CHRONICLE" for doc in data["results"])

    @pytest.mark.asyncio
    async def test_paginate_through_documents(
        self, client: AsyncClient, test_document: Document
    ) -> None:
        """Test paginating through document search results."""
        response = await client.post(
            f"/worlds/{test_document.world_id}/documents/search",
            json={
                "limit": 5,
                "offset": 0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5
