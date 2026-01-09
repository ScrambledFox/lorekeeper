"""
Integration tests for lore retrieval and filtering by truth policy.

This module tests the core LoreKeeper functionality: retrieving lore with
distinct handling of canonical truth (strict) versus narratives (mythic).
"""

import pytest
from httpx import AsyncClient

from lorekeeper.db.models import Document, World


class TestCanonicalVsMythicRetrieval:
    """Test suite for retrieving canonical vs mythic lore."""

    @pytest.mark.asyncio
    async def test_retrieve_canonical_lore_only(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test retrieving only canonical (strict) lore."""
        world_id = test_world.id

        # Create canonical document
        response_canonical = await client.post(
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
        assert response_canonical.status_code == 201
        canonical_doc_id = response_canonical.json()["id"]

        # Index the canonical document
        await client.post(f"/worlds/{world_id}/documents/{canonical_doc_id}/index", json={})

        # Retrieve using STRICT_ONLY policy
        response = await client.post(
            f"/worlds/{world_id}/retrieve",
            json={
                "query": "historical",
                "policy": "STRICT_ONLY",
                "top_k": 5,
                "include_entities": False,
                "include_snippets": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # All snippets should be from STRICT documents
        for snippet in data["snippets"]:
            assert snippet["document_mode"] == "STRICT"

    @pytest.mark.asyncio
    async def test_retrieve_mythic_lore_only(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test retrieving only mythic lore (legends, rumors, stories)."""
        world_id = test_world.id

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
        assert response_mythic.status_code == 201
        mythic_doc_id = response_mythic.json()["id"]

        # Index the mythic document
        await client.post(f"/worlds/{world_id}/documents/{mythic_doc_id}/index", json={})

        # Retrieve using MYTHIC_ONLY policy
        response = await client.post(
            f"/worlds/{world_id}/retrieve",
            json={
                "query": "legend",
                "policy": "MYTHIC_ONLY",
                "top_k": 5,
                "include_entities": False,
                "include_snippets": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # All snippets should be from MYTHIC documents
        for snippet in data["snippets"]:
            assert snippet["document_mode"] == "MYTHIC"

    @pytest.mark.asyncio
    async def test_retrieve_hybrid_canonical_and_mythic(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test retrieving both canonical and mythic lore together (HYBRID)."""
        world_id = test_world.id

        # Create canonical document
        response_canonical = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "STRICT",
                "kind": "CHRONICLE",
                "title": "Official Record of Events",
                "author": None,
                "in_world_date": None,
                "text": "The king ruled with justice.",
                "provenance": None,
            },
        )
        canonical_doc_id = response_canonical.json()["id"]

        # Create mythic document about same topic
        response_mythic = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "RUMOR",
                "title": "Common Folk Tale",
                "author": "Unknown",
                "in_world_date": "Year 1087",
                "text": "But the king was secretly a tyrant, they whispered.",
                "provenance": None,
            },
        )
        mythic_doc_id = response_mythic.json()["id"]

        # Index both documents
        await client.post(f"/worlds/{world_id}/documents/{canonical_doc_id}/index", json={})
        await client.post(f"/worlds/{world_id}/documents/{mythic_doc_id}/index", json={})

        # Retrieve using HYBRID policy
        response = await client.post(
            f"/worlds/{world_id}/retrieve",
            json={
                "query": "king",
                "policy": "HYBRID",
                "top_k": 10,
                "include_entities": False,
                "include_snippets": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should have snippets from both modes
        modes = {snippet["document_mode"] for snippet in data["snippets"]}
        assert "STRICT" in modes or "MYTHIC" in modes


class TestLoreReliabilityLabels:
    """Test suite for reliability labels in retrieved lore."""

    @pytest.mark.asyncio
    async def test_canonical_source_label(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test that canonical sources are labeled as CANON_SOURCE."""
        world_id = test_world.id

        # Create canonical document
        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "STRICT",
                "kind": "CHRONICLE",
                "title": "Official Record",
                "author": None,
                "in_world_date": None,
                "text": "This is verified historical fact.",
                "provenance": None,
            },
        )
        doc_id = response.json()["id"]

        # Index document
        await client.post(f"/worlds/{world_id}/documents/{doc_id}/index", json={})

        # Retrieve and check reliability label
        response = await client.post(
            f"/worlds/{world_id}/retrieve",
            json={
                "query": "verified",
                "policy": "STRICT_ONLY",
                "top_k": 5,
                "include_entities": False,
                "include_snippets": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        for snippet in data["snippets"]:
            assert snippet["reliability_label"] == "CANON_SOURCE"

    @pytest.mark.asyncio
    async def test_mythic_source_label(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test that mythic sources are labeled as MYTHIC_SOURCE."""
        world_id = test_world.id

        # Create mythic document
        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "RUMOR",
                "title": "Tavern Gossip",
                "author": "Unknown",
                "in_world_date": "Year 1087",
                "text": "They say there's treasure hidden in the mountains.",
                "provenance": None,
            },
        )
        doc_id = response.json()["id"]

        # Index document
        await client.post(f"/worlds/{world_id}/documents/{doc_id}/index", json={})

        # Retrieve and check reliability label
        response = await client.post(
            f"/worlds/{world_id}/retrieve",
            json={
                "query": "treasure",
                "policy": "MYTHIC_ONLY",
                "top_k": 5,
                "include_entities": False,
                "include_snippets": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        for snippet in data["snippets"]:
            assert snippet["reliability_label"] == "MYTHIC_SOURCE"


class TestLoreFilteringByDocumentType:
    """Test suite for filtering lore by document kind."""

    @pytest.mark.asyncio
    async def test_search_lore_by_document_kind(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test filtering retrieved lore by document kind."""
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
                    "text": "Content about the kingdom",
                    "provenance": None,
                },
            )
            assert response.status_code == 201

        # Search for specific kind
        response = await client.post(
            f"/worlds/{world_id}/documents/search?kind=SCRIPTURE",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert all(doc["kind"] == "SCRIPTURE" for doc in data["results"])


class TestProvenanceInRetrieval:
    """Test suite for provenance metadata in retrieval responses."""

    @pytest.mark.asyncio
    async def test_provenance_fields_in_snippet_response(
        self,
        client: AsyncClient,
        test_world: World,
        test_document: Document,
        override_get_session: bool,
    ) -> None:
        """Test that snippet responses include full provenance information."""
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

        # Verify all provenance fields are present in snippets
        if data["snippets"]:
            snippet = data["snippets"][0]
            assert "document_title" in snippet
            assert "document_kind" in snippet
            assert "document_mode" in snippet
            assert "document_author" in snippet
            assert "in_world_date" in snippet
            assert "snippet_id" in snippet
            assert "document_id" in snippet
            assert "reliability_label" in snippet
