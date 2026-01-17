#!/usr/bin/env python3
"""
Database seed script to create an initial world with sample data.

Run this after migrations are applied:
    uv run python lorekeeper/db/seed.py
"""

import asyncio
from uuid import uuid4

from app.db.database import AsyncSessionLocal
from app.db.utils import utc_now
from app.models.domain import Document, Entity, World


async def seed_initial_world() -> None:
    """Create an initial world with sample entities and documents."""
    async with AsyncSessionLocal() as session:
        # Create a world
        world_id = uuid4()
        world = World(
            id=world_id,
            name="Aethermoor",
            description="A mystical realm where ancient magic flows through forgotten kingdoms.",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(world)
        await session.flush()  # Flush to ensure world is created before adding relationships

        # Create sample entities (strict canon)
        entities = [
            Entity(
                id=uuid4(),
                world_id=world_id,
                type="Character",
                canonical_name="King Aldren",
                aliases=["Aldren the Wise", "The Last King"],
                summary="Ruler of the Northern Kingdoms",
                description="King Aldren ruled the Northern Kingdoms from the year 1000 to 1032. He was known for his diplomatic prowess and his love of ancient lore.",
                tags=["ruler", "diplomat", "ancient_lore", "deceased"],
                is_fiction=False,
                status="ACTIVE",
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
            Entity(
                id=uuid4(),
                world_id=world_id,
                type="Location",
                canonical_name="Lake Silvermere",
                aliases=["The Silver Lake", "Mirror of Stars"],
                summary="An ancient lake at the heart of the Northern Kingdoms",
                description="Lake Silvermere is an ancient glacial lake surrounded by crystal caves. Its waters are said to reflect not only light but also glimpses of other times.",
                tags=["ancient", "magical", "sacred"],
                is_fiction=False,
                status="ACTIVE",
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
            Entity(
                id=uuid4(),
                world_id=world_id,
                type="Faction",
                canonical_name="The Circle of Whispers",
                aliases=["The Whispers", "Circle"],
                summary="An order of scholars and mages",
                description="The Circle of Whispers is an ancient order dedicated to preserving forbidden knowledge and studying the nature of reality itself.",
                tags=["scholars", "mages", "secret", "ancient"],
                is_fiction=False,
                status="ACTIVE",
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
            Entity(
                id=uuid4(),
                world_id=world_id,
                type="Creature",
                canonical_name="Scibble",
                aliases=["Scibbles", "Star Scuttler"],
                summary="A whimsical in-lore fantasy creature from tavern tales",
                description="Scibbles are small, bioluminescent creatures said to inhabit the deeper caverns beneath Lake Silvermere. They are described as harmless and curious, with the ability to mimic sounds and lights. Most scholars dismiss them as myth, though some believe they are a real, undocumented species.",
                tags=["fantasy", "creature", "undocumented", "bioluminescent"],
                is_fiction=True,
                status="ACTIVE",
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
        ]

        for entity in entities:
            session.add(entity)
        await session.flush()  # Flush to ensure entities are created before documents

        # Create sample documents (strict and mythic)
        documents = [
            Document(
                id=uuid4(),
                world_id=world_id,
                mode="STRICT",
                kind="TEXTBOOK",
                title="The Annals of the Northern Kingdoms",
                author="Lord Archivist Matthus",
                in_world_date="Year 1150",
                text="The Northern Kingdoms were ruled by the line of Aldren for over two centuries. King Aldren (1000-1032) was the last of his line. After his death, the kingdoms fell into decline, and no single ruler emerged to unite them again. The exact circumstances of his death remain disputed, though most scholars agree he died of natural causes.",
                provenance={"source": "historical_archive", "authenticity": "high"},
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
            Document(
                id=uuid4(),
                world_id=world_id,
                mode="MYTHIC",
                kind="RUMOR",
                title="The Tale of Aldren the Immortal",
                author="Unknown wanderer",
                in_world_date="Unknown",
                text="Some say King Aldren did not truly die. Instead, they whisper, he sought refuge beneath Lake Silvermere, where the waters granted him eternal life. On certain nights when the stars align, fishermen report seeing a crowned figure walking the lake bottom, watching the world above. Aldren still lives, they say, waiting for the day when his people will call him back to rule.",
                provenance={"source": "tavern_tales", "authenticity": "low"},
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
            Document(
                id=uuid4(),
                world_id=world_id,
                mode="MYTHIC",
                kind="SCRIPTURE",
                title="The Book of Stars (Fragment)",
                author="The Circle of Whispers (attributed)",
                in_world_date="Year 876 (copied)",
                text="In the depths of knowing lies the truth of transformation. The lake that mirrors stars also mirrors souls. Those pure of heart may drink and understand. Those impure shall see only their own reflection. The king sought this knowledge, but pride closed his eyes. Thus he remains, neither living nor dead, locked between worlds.",
                provenance={"source": "forbidden_archive", "authenticity": "unknown"},
                created_at=utc_now(),
                updated_at=utc_now(),
            ),
        ]

        for document in documents:
            session.add(document)

        # Commit all changes
        await session.commit()
        print("✓ Seed data created successfully")
        print("  - World: Aethermoor")
        print(f"  - Entities: {len(entities)}")
        print("    - Fact entities: 3 (King Aldren, Lake Silvermere, The Circle of Whispers)")
        print("    - Fiction entities: 1 (Scibble)")
        print(f"  - Documents: {len(documents)}")


async def main() -> None:
    """Main entry point."""
    try:
        await seed_initial_world()
    except Exception as e:
        print(f"✗ Error during seeding: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
