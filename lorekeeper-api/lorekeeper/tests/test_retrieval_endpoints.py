"""
Integration tests for Retrieval API endpoints.
"""

import pytest
from httpx import AsyncClient

from lorekeeper.models.domain import Document, DocumentSnippet, Entity, World


class TestRetrievalEndpoints:
    """Test suite for Retrieval endpoints."""

    @pytest.mark.asyncio
    async def test_retrieve_basic_hybrid(
        self, client: AsyncClient, test_world: World, test_document_snippet: DocumentSnippet
    ) -> None:
        """Test basic retrieval with HYBRID policy."""
        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "test document",
                "policy": "HYBRID",
                "top_k": 10,
                "include_entities": False,
                "include_snippets": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test document"
        assert data["policy"] == "HYBRID"
        assert "snippets" in data
        assert len(data["snippets"]) > 0

    @pytest.mark.asyncio
    async def test_retrieve_strict_only(
        self, client: AsyncClient, test_world: World, test_document: Document
    ) -> None:
        """Test retrieval with STRICT_ONLY policy."""
        # Index the document first
        await client.post(
            f"/worlds/{test_world.id}/documents/{test_document.id}/index",
            json={},
        )

        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "test",
                "policy": "STRICT_ONLY",
                "include_snippets": True,
                "include_entities": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        # All snippets should be from STRICT documents
        for snippet in data["snippets"]:
            assert snippet["document_mode"] == "STRICT"
            assert snippet["reliability_label"] == "CANON_SOURCE"

    @pytest.mark.asyncio
    async def test_retrieve_mythic_only(self, client: AsyncClient, test_world: World) -> None:
        """Test retrieval with MYTHIC_ONLY policy."""
        # Create a mythic document
        doc_response = await client.post(
            f"/worlds/{test_world.id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "RUMOR",
                "title": "A Tale",
                "text": "Once upon a time there was a great hero. The hero was brave and strong.",
            },
        )
        doc_id = doc_response.json()["id"]

        # Index it
        await client.post(f"/worlds/{test_world.id}/documents/{doc_id}/index", json={})

        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "hero",
                "policy": "MYTHIC_ONLY",
                "include_snippets": True,
                "include_entities": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        # All snippets should be from MYTHIC documents
        for snippet in data["snippets"]:
            assert snippet["document_mode"] == "MYTHIC"
            assert snippet["reliability_label"] == "MYTHIC_SOURCE"

    @pytest.mark.asyncio
    async def test_retrieve_with_entities(
        self, client: AsyncClient, test_world: World, test_entity: Entity
    ) -> None:
        """Test retrieval including entities."""
        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "Hero",
                "policy": "HYBRID",
                "include_entities": True,
                "include_snippets": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "entities" in data

    @pytest.mark.asyncio
    async def test_retrieve_invalid_policy(self, client: AsyncClient, test_world: World) -> None:
        """Test retrieval with invalid policy."""
        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "test",
                "policy": "INVALID_POLICY",
            },
        )

        assert response.status_code == 400
        assert "Invalid policy" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retrieve_snippet_provenance(
        self, client: AsyncClient, test_world: World, test_document: Document
    ) -> None:
        """Test that retrieved snippets include proper provenance."""
        # Index the document
        await client.post(
            f"/worlds/{test_world.id}/documents/{test_document.id}/index",
            json={},
        )

        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "test",
                "policy": "HYBRID",
                "include_snippets": True,
                "include_entities": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        if data["snippets"]:
            snippet = data["snippets"][0]
            assert snippet["document_title"] is not None
            assert snippet["document_kind"] is not None
            assert snippet["document_mode"] is not None
            assert "snippet_text" in snippet
            assert "snippet_id" in snippet

    @pytest.mark.asyncio
    async def test_retrieve_similarity_scoring(
        self, client: AsyncClient, test_world: World, test_document_snippet: DocumentSnippet
    ) -> None:
        """Test that snippets include similarity scores."""
        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "test",
                "policy": "HYBRID",
                "include_snippets": True,
                "include_entities": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        if data["snippets"]:
            snippet = data["snippets"][0]
            assert "similarity_score" in snippet
            # Score should be between -1 and 1
            if snippet["similarity_score"] is not None:
                assert -1.0 <= snippet["similarity_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_retrieve_respects_top_k(
        self, client: AsyncClient, test_world: World, test_document: Document
    ) -> None:
        """Test that retrieval respects top_k parameter."""
        # Index the document
        await client.post(
            f"/worlds/{test_world.id}/documents/{test_document.id}/index",
            json={},
        )

        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "test",
                "policy": "HYBRID",
                "top_k": 1,
                "include_snippets": True,
                "include_entities": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["snippets"]) <= 1

    @pytest.mark.asyncio
    async def test_retrieve_hybrid_ordering(self, client: AsyncClient, test_world: World) -> None:
        """Test that HYBRID policy orders STRICT before MYTHIC."""
        # Create and index both strict and mythic documents
        strict_response = await client.post(
            f"/worlds/{test_world.id}/documents",
            json={
                "mode": "STRICT",
                "kind": "CHRONICLE",
                "title": "Strict",
                "text": "A strict canonical document about heroes",
            },
        )
        strict_id = strict_response.json()["id"]

        mythic_response = await client.post(
            f"/worlds/{test_world.id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "RUMOR",
                "title": "Mythic",
                "text": "A mythic tale about legendary heroes",
            },
        )
        mythic_id = mythic_response.json()["id"]

        # Index both
        await client.post(f"/worlds/{test_world.id}/documents/{strict_id}/index", json={})
        await client.post(f"/worlds/{test_world.id}/documents/{mythic_id}/index", json={})

        response = await client.post(
            f"/worlds/{test_world.id}/retrieve",
            json={
                "query": "heroes",
                "policy": "HYBRID",
                "include_snippets": True,
                "include_entities": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # First result should be CANON_SOURCE if both exist
        if len(data["snippets"]) > 1:
            assert data["snippets"][0]["reliability_label"] == "CANON_SOURCE"
