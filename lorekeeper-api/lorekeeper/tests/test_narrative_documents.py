"""
Integration tests for narrative documents (mythic and strict lore).

This module tests the creation, storage, and retrieval of narrative documents
that form the core of LoreKeeper's lore management system.
"""

from typing import Any

import pytest
from httpx import AsyncClient

from lorekeeper.models.domain import World


class TestNarrativeDocumentCreation:
    """Test suite for creating and storing narrative documents."""

    @pytest.mark.asyncio
    async def test_create_sacred_scripture(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test creating a sacred scripture document for mythic lore."""
        world_id = test_world.id

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
    async def test_create_canonical_chronicle(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test creating a canonical chronicle document for strict lore."""
        world_id = test_world.id

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


class TestNarrativeKinds:
    """Test suite for different kinds of narrative documents."""

    @pytest.mark.asyncio
    async def test_create_tavern_rumor(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test creating a tavern rumor as an unverified narrative."""
        world_id = test_world.id

        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "RUMOR",
                "title": "Tavern Tales: The Duke Who Never Dies",
                "author": "Unknown (Various Drunken Patrons)",
                "in_world_date": "Year 1087",
                "text": "They say Duke Rhalos died 70 years ago, but I've seen him walking the night roads...",
                "provenance": {"source": "tavern_gossip", "reliability": "unverified"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["kind"] == "RUMOR"
        assert data["mode"] == "MYTHIC"

    @pytest.mark.asyncio
    async def test_create_in_world_ballad(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test creating a ballad, a poetic narrative from the world."""
        world_id = test_world.id

        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "BALLAD",
                "title": "The Ballad of Heroes",
                "author": "Bard Theron",
                "in_world_date": "Year 900",
                "text": "Sing of the heroes of old, whose deeds echo through the ages...",
                "provenance": {"source": "oral_tradition"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["kind"] == "BALLAD"

    @pytest.mark.asyncio
    async def test_create_propaganda_document(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test creating a propaganda document as intentionally biased narrative."""
        world_id = test_world.id

        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "PROPAGANDA",
                "title": "The Glory of the Empire",
                "author": "Imperial Ministry",
                "in_world_date": "Year 1080",
                "text": "Under the benevolent rule of the Emperor, all lands prosper...",
                "provenance": {"source": "state_publication", "bias": "high"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["kind"] == "PROPAGANDA"

    @pytest.mark.asyncio
    async def test_create_memoir(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test creating a personal memoir as a subjective narrative."""
        world_id = test_world.id

        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "MEMOIR",
                "title": "My Life in Exile",
                "author": "Lord Brennan",
                "in_world_date": "Year 1070",
                "text": "I was cast out from my homeland, forced to wander foreign lands...",
                "provenance": {"source": "personal_account", "subject": "Lord Brennan"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["kind"] == "MEMOIR"


class TestProvenanceTracking:
    """Test suite for document provenance tracking and attribution."""

    @pytest.mark.asyncio
    async def test_document_provenance_storage(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test that document provenance metadata is stored correctly."""
        world_id = test_world.id

        provenance_data: dict[str, Any] = {
            "source": "ancient_ruins",
            "discovered_by": "Expedition Team",
            "expedition_date": "Year 1087",
            "condition": "fragmented",
            "translations": 2,
        }

        response = await client.post(
            f"/worlds/{world_id}/documents",
            json={
                "mode": "MYTHIC",
                "kind": "TEXTBOOK",
                "title": "Ancient Writings from the Ruins",
                "author": "Unknown",
                "in_world_date": "Unknown",
                "text": "Fragmentary writings describing ancient rituals...",
                "provenance": provenance_data,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["provenance"] == provenance_data


class TestInWorldContext:
    """Test suite for in-world context and dating systems."""

    @pytest.mark.asyncio
    async def test_various_in_world_date_formats(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test that documents support flexible in-world dating systems."""
        world_id = test_world.id

        date_formats = [
            "Year -500 (Ancient Prophecy)",
            "Year 1050",
            "3rd Age, Spring Equinox",
            "The Time Before Memory",
            "Undated Fragment",
        ]

        for in_world_date in date_formats:
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
    async def test_in_world_author_attribution(
        self, client: AsyncClient, test_world: World, override_get_session: bool
    ) -> None:
        """Test that in-world author attribution is preserved."""
        world_id = test_world.id

        authors = [
            "High Priestess Aella",
            "Royal Historian",
            "Unknown (Various Drunken Patrons)",
            "Bard Theron",
            "Anonymous Exile",
        ]

        for author in authors:
            response = await client.post(
                f"/worlds/{world_id}/documents",
                json={
                    "mode": "MYTHIC",
                    "kind": "CHRONICLE",
                    "title": f"Work by {author}",
                    "author": author,
                    "in_world_date": "Year 1087",
                    "text": "Content",
                    "provenance": None,
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["author"] == author
