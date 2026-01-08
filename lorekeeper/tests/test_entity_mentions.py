"""
Integration tests for entity mention linking functionality.

This module tests manual and automated entity mention linking, confidence scoring,
and retrieval of linked entities within document snippets.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.db.models import Document, DocumentSnippet, Entity, World


class TestManualEntityMentionLinking:
    """Test suite for manually linking entities to snippets."""

    @pytest.mark.asyncio
    async def test_link_entity_to_snippet(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document: Document,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test creating a manual entity mention."""
        response = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "TestHero",
                "confidence": 1.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["entity_id"] == str(test_entity.id)
        assert data["mention_text"] == "TestHero"
        assert data["confidence"] == 1.0
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_link_entity_with_partial_confidence(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test creating an entity mention with partial confidence."""
        response = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "Hero (might be TestHero)",
                "confidence": 0.65,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["confidence"] == 0.65

    @pytest.mark.asyncio
    async def test_cannot_link_same_entity_twice(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test that duplicate mentions to the same entity are rejected."""
        # Create first mention
        response1 = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "TestHero",
                "confidence": 1.0,
            },
        )
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "TestHero",
                "confidence": 1.0,
            },
        )
        assert response2.status_code == 409

    @pytest.mark.asyncio
    async def test_link_nonexistent_entity_fails(
        self,
        client: AsyncClient,
        test_world: World,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test that linking a nonexistent entity returns 404."""
        from uuid import uuid4

        response = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(uuid4()),
                "mention_text": "Nonexistent",
                "confidence": 1.0,
            },
        )
        assert response.status_code == 404


class TestEntityMentionRetrieval:
    """Test suite for retrieving entity mentions."""

    @pytest.mark.asyncio
    async def test_get_snippet_mentions(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test retrieving all mentions for a snippet."""
        # Create a mention
        await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "TestHero",
                "confidence": 1.0,
            },
        )

        # Retrieve mentions
        response = await client.get(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["mention_text"] == "TestHero"
        assert data[0]["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_get_snippet_with_mentions(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test retrieving a snippet with all its mentions."""
        # Create a mention
        await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "TestHero",
                "confidence": 1.0,
            },
        )

        # Get snippet with mentions
        response = await client.get(f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["snippet_id"] == str(test_document_snippet.id)
        assert "mentions" in data
        assert len(data["mentions"]) >= 1
        assert data["mentions"][0]["mention_text"] == "TestHero"

    @pytest.mark.asyncio
    async def test_empty_mentions_list_for_new_snippet(
        self,
        client: AsyncClient,
        test_world: World,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test that a new snippet has empty mentions."""
        response = await client.get(f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}")

        assert response.status_code == 200
        data = response.json()
        assert "mentions" in data
        assert len(data["mentions"]) == 0


class TestAutomatedEntityMentionLinking:
    """Test suite for automated entity mention linking."""

    @pytest.mark.asyncio
    async def test_auto_link_by_canonical_name(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test automated linking finds canonical entity names."""
        # Create a document with entity name in text
        doc_text = "The hero TestHero walked into the tavern."
        from lorekeeper.db.models import Document

        doc = Document(
            world_id=test_world.id,
            mode="STRICT",
            kind="CHRONICLE",
            title="Hero's Journey",
            author="Scribe",
            text=doc_text,
        )
        db_session.add(doc)
        await db_session.flush()
        await db_session.refresh(doc)

        # Index to create snippet
        response_index = await client.post(
            f"/worlds/{test_world.id}/documents/{doc.id}/index", json={}
        )
        assert response_index.status_code == 200
        snippet_ids = response_index.json()["snippet_ids"]

        # Auto-link
        response = await client.post(
            f"/worlds/{test_world.id}/snippets/{snippet_ids[0]}/auto-link",
            json={"confidence_threshold": 0.0},
        )

        assert response.status_code == 200
        data = response.json()
        # Should find the canonical name "TestHero"
        assert any(m["mention_text"] == "TestHero" for m in data)

    @pytest.mark.asyncio
    async def test_auto_link_respects_confidence_threshold(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        db_session: AsyncSession,
        override_get_session: bool,
    ) -> None:
        """Test that auto-linking respects the confidence threshold."""
        from lorekeeper.db.models import Document

        # Create document with entity alias
        doc_text = "The hero Hero walked into the tavern."
        doc = Document(
            world_id=test_world.id,
            mode="STRICT",
            kind="CHRONICLE",
            title="Hero's Journey",
            author="Scribe",
            text=doc_text,
        )
        db_session.add(doc)
        await db_session.flush()
        await db_session.refresh(doc)

        # Index to create snippet
        response_index = await client.post(
            f"/worlds/{test_world.id}/documents/{doc.id}/index", json={}
        )
        assert response_index.status_code == 200
        snippet_ids = response_index.json()["snippet_ids"]

        # Auto-link with high threshold (aliases have 0.95 confidence)
        response = await client.post(
            f"/worlds/{test_world.id}/snippets/{snippet_ids[0]}/auto-link",
            json={"confidence_threshold": 0.99},
        )

        assert response.status_code == 200
        data = response.json()
        # Should not include the alias since threshold is too high
        assert not any(m["mention_text"] == "Hero" for m in data)

    @pytest.mark.asyncio
    async def test_auto_link_with_overwrite(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test that auto-linking can overwrite existing mentions."""
        # Create a manual mention with low confidence
        await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "Old text",
                "confidence": 0.3,
            },
        )

        # Auto-link with overwrite=True (should update)
        response = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/auto-link",
            json={"confidence_threshold": 0.0, "overwrite": True},
        )

        assert response.status_code == 200


class TestDeleteEntityMention:
    """Test suite for deleting entity mentions."""

    @pytest.mark.asyncio
    async def test_delete_mention(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test deleting an entity mention."""
        # Create a mention
        response_create = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "TestHero",
                "confidence": 1.0,
            },
        )
        mention_id = response_create.json()["id"]

        # Delete the mention
        response_delete = await client.delete(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions/{mention_id}"
        )

        assert response_delete.status_code == 204

        # Verify it's gone
        response_get = await client.get(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions"
        )
        assert len(response_get.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_nonexistent_mention_fails(
        self,
        client: AsyncClient,
        test_world: World,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test that deleting a nonexistent mention returns 404."""
        from uuid import uuid4

        response = await client.delete(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions/{uuid4()}"
        )
        assert response.status_code == 404


class TestMentionConfidenceScoring:
    """Test suite for confidence scoring in entity mentions."""

    @pytest.mark.asyncio
    async def test_canonical_name_has_perfect_confidence(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test that canonical names have confidence of 1.0."""
        response = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "TestHero",
                "confidence": 1.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_alias_has_lower_confidence(
        self,
        client: AsyncClient,
        test_world: World,
        test_entity: Entity,
        test_document_snippet: DocumentSnippet,
        override_get_session: bool,
    ) -> None:
        """Test that aliases get slightly lower confidence than canonical names."""
        response = await client.post(
            f"/worlds/{test_world.id}/snippets/{test_document_snippet.id}/mentions",
            json={
                "entity_id": str(test_entity.id),
                "mention_text": "Hero",  # This is an alias
                "confidence": 0.95,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["confidence"] == 0.95
