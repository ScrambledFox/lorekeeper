"""
Integration tests for Document API endpoints.
"""

import pytest
from httpx import AsyncClient

from lorekeeper.db.models import Document, World


class TestDocumentEndpoints:
    """Test suite for Document endpoints."""

    @pytest.mark.asyncio
    async def test_create_document(self, client: AsyncClient, test_world: World) -> None:
        """Test creating a document."""
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
    async def test_create_document_mythic(self, client: AsyncClient, test_world: World) -> None:
        """Test creating a mythic document."""
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
    async def test_get_document(self, client: AsyncClient, test_document: Document) -> None:
        """Test getting a document by ID."""
        response = await client.get(
            f"/worlds/{test_document.world_id}/documents/{test_document.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_document.id)
        assert data["title"] == test_document.title
        assert data["mode"] == test_document.mode

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, client: AsyncClient, test_world: World) -> None:
        """Test getting a non-existent document."""
        from uuid import uuid4

        response = await client.get(f"/worlds/{test_world.id}/documents/{uuid4()}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_index_document(self, client: AsyncClient, test_document: Document) -> None:
        """Test indexing a document."""
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
        assert data["snippets_created"] >= 1
        assert len(data["snippet_ids"]) >= 1

    @pytest.mark.asyncio
    async def test_search_documents_by_title(
        self, client: AsyncClient, test_document: Document
    ) -> None:
        """Test searching documents by title."""
        response = await client.post(
            f"/worlds/{test_document.world_id}/documents/search",
            json={"query": "Test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(doc["title"] == "Test Document" for doc in data["results"])

    @pytest.mark.asyncio
    async def test_search_documents_by_mode(self, client: AsyncClient, test_world: World) -> None:
        """Test searching documents by mode."""
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
    async def test_search_documents_by_kind(
        self, client: AsyncClient, test_document: Document
    ) -> None:
        """Test searching documents by kind."""
        response = await client.post(
            f"/worlds/{test_document.world_id}/documents/search",
            json={"kind": "CHRONICLE"},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(doc["kind"] == "CHRONICLE" for doc in data["results"])

    @pytest.mark.asyncio
    async def test_search_documents_pagination(
        self, client: AsyncClient, test_document: Document
    ) -> None:
        """Test document search pagination."""
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
