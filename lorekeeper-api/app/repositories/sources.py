"""Source repository for data access."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api.sources import SourceChunkCreate, SourceCreate
from app.models.db.sources import Source, SourceChunk


class SourceRepository:
    """Repository for source persistence and queries."""

    async def add_source(self, session: AsyncSession, source: SourceCreate) -> Source:
        db_source = Source(
            world_id=source.world_id,
            type=source.type,
            title=source.title,
            author_ids=source.author_ids,
            origin=source.origin,
            book_version_id=source.book_version_id,
            meta=source.meta,
        )
        session.add(db_source)
        await session.flush()
        return db_source

    async def get_source(self, session: AsyncSession, source_id: str) -> Source | None:
        return await session.get(Source, source_id)

    async def add_source_chunks(
        self, session: AsyncSession, source_id: str, chunks: list[SourceChunkCreate]
    ) -> list[SourceChunk]:
        db_chunks = [
            SourceChunk(
                source_id=source_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=chunk.embedding,
                meta=chunk.meta,
            )
            for chunk in chunks
        ]
        session.add_all(db_chunks)
        await session.flush()
        return db_chunks

    async def add_chunks(self, session: AsyncSession, chunks: list[SourceChunk]) -> None:
        session.add_all(chunks)
