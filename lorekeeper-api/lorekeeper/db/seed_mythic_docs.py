"""
Seed script to add example mythic documents for Milestone E demonstration.
Run this after creating a world and entities.
"""

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lorekeeper.models.domain import Document, World

# Example mythic documents for demonstration
EXAMPLE_MYTHIC_DOCS: list[dict[str, Any]] = [
    {
        "title": "The Prophecy of the Three Moons",
        "mode": "MYTHIC",
        "kind": "SCRIPTURE",
        "author": "High Priestess Aella",
        "in_world_date": "Year -500 (Ancient Prophecy)",
        "text": """In the age when three moons align in the crimson sky, a great shadow shall fall upon the land.

The firstborn child of the dragon line shall not be what they seem. Born in flame, they shall walk in light,
yet darkness shall follow their steps. Kingdoms shall rise and fall by their hand, and many shall whisper:
'Is this our savior or our doom?'

When the elder moons fade and only the silver moon remains, truth shall be revealed. But the price of truth
is often paid in blood and tears. Choose wisely, children of this world, for the prophecy cares not for your hearts.""",
        "provenance": {"source": "ancient_religious_text", "confidence": "low"},
    },
    {
        "title": "Tavern Tales: The Duke Who Never Dies",
        "mode": "MYTHIC",
        "kind": "RUMOR",
        "author": "Unknown (Various Drunken Patrons)",
        "in_world_date": "Year 1087 (Current Year)",
        "text": """They say Duke Rhalos died in the Battle of Crimson Fields seventy years ago. But I've seen him,
        I swear it on my mother's grave. He walks the night roads still, never aging, never tiring.

Some claim he made a pact with the old magic. Others say he drank a poison meant to kill him, but it changed
him instead. The worst stories—the ones whispered only when three ales deep—say he's not the Duke anymore.
That something else wears his face.

Last month, a merchant swore he saw him near the northern tower. The Duke's tower, where his daughter still waits,
they say, never believing her father would truly leave her. Mad, they call her now. But what if she knows something?
What if the impossible is just waiting for someone brave enough to seek it?""",
        "provenance": {"source": "tavern_gossip", "reliability": "unverified"},
    },
    {
        "title": "The Counter-Chronicle of House Valorian",
        "mode": "MYTHIC",
        "kind": "CHRONICLE",
        "author": "Scribe Therion (Unauthorized Account)",
        "in_world_date": "Year 1050",
        "text": """The official histories speak of House Valorian as paragons of virtue, noble knights and just rulers.

But this is not the account I witnessed. In that year, when the great famine came, the lords of Valorian
did not open their granaries to feed the starving commons. Instead, they hoarded. They bought up land from
desperate farmers at copper prices. They built walls higher, not to defend against invaders, but to keep
the hungry masses beyond their gates.

I was there. I saw the children crying outside those walls. I heard the prayers for justice that went unanswered.
Some histories are written by victors. This one is written by a survivor who could not forget what he witnessed.

Let the reader decide which account is true: the glittering lies in marble halls, or the bitter truth told here.""",
        "provenance": {"source": "suppressed_historical_account", "archived": True},
    },
]


async def seed_mythic_documents(world_id: str) -> None:
    """
    Add example mythic documents to a world.

    Args:
        world_id: UUID of the world to add documents to
    """
    # Get database URL from environment
    import os

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://lorekeeper:lorekeeper_dev_password@localhost/lorekeeper",
    )

    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Verify world exists
        stmt = select(World).where(World.id == UUID(world_id))
        world = await session.scalar(stmt)

        if not world:
            print(f"Error: World {world_id} not found")
            return

        print(f"Adding example mythic documents to world: {world.name}")

        # Create and add example documents
        for doc_data in EXAMPLE_MYTHIC_DOCS:
            doc = Document(
                world_id=UUID(world_id),
                mode=doc_data["mode"],
                kind=doc_data["kind"],
                title=doc_data["title"],
                author=doc_data["author"],
                in_world_date=doc_data["in_world_date"],
                text=doc_data["text"],
                provenance=doc_data["provenance"],
            )
            session.add(doc)
            print(f"  Added: {doc_data['title']} ({doc_data['kind']})")

        await session.commit()
        print(f"Successfully added {len(EXAMPLE_MYTHIC_DOCS)} example mythic documents")

    await engine.dispose()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python seed_mythic_docs.py <world_id>")
        print("Example: python seed_mythic_docs.py 550e8400-e29b-41d4-a716-446655440000")
        sys.exit(1)

    world_id = sys.argv[1]
    asyncio.run(seed_mythic_documents(world_id))
