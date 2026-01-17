"""Source service for domain logic and embeddings."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, InternalServerErrorException, NotFoundException
from app.models.api.sources import SourceChunkCreate, SourceCreate
from app.models.db.sources import Source, SourceChunk
from app.repositories.sources import SourceRepository
from app.services.embedding import EmbeddingService, EmbeddingServiceError
from app.services.embedding_factory import get_embedding_service
from app.types.embedding import EmbeddingOptions, EmbeddingPurpose


class SourceService:
    """Service for source creation and chunk embeddings."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        repository: SourceRepository | None = None,
    ) -> None:
        self._embedding_service = embedding_service or get_embedding_service()
        self._repository = repository or SourceRepository()

    async def create_source(self, session: AsyncSession, source: SourceCreate) -> Source:
        """Create a source."""
        try:
            db_source = await self._repository.add_source(session, source)
            await session.commit()
            await session.refresh(db_source)
            return db_source
        except Exception:
            await session.rollback()
            raise

    async def get_source(self, session: AsyncSession, source_id: str) -> Source:
        """Get a source by ID."""
        db_source = await self._repository.get_source(session, source_id)
        if not db_source:
            raise NotFoundException(resource="Source", id=source_id)
        return db_source

    async def create_source_chunks(
        self,
        session: AsyncSession,
        source_id: str,
        chunks: list[SourceChunkCreate],
    ) -> list[SourceChunk]:
        """Create source chunks and generate embeddings if needed."""
        try:
            source = await self._repository.get_source(session, source_id)
            if not source:
                raise NotFoundException(resource="Source", id=source_id)

            if not chunks:
                return []

            for chunk in chunks:
                if str(chunk.source_id) != source_id:
                    raise BadRequestException("Chunk source_id must match the path source_id")

            texts_to_embed = [chunk.content for chunk in chunks if chunk.embedding is None]
            embeddings: list[list[float]] = []
            if texts_to_embed:
                options = EmbeddingOptions(
                    model="source_chunks_v1", purpose=EmbeddingPurpose.SOURCE_CHUNK
                )
                try:
                    embedding_results = self._embedding_service.embed_batch(texts_to_embed, options)
                except EmbeddingServiceError as exc:
                    raise InternalServerErrorException(message=str(exc)) from exc

                if any(result.error or result.vector is None for result in embedding_results):
                    error_messages = [
                        result.error.message
                        for result in embedding_results
                        if result.error is not None
                    ]
                    raise InternalServerErrorException(
                        message=f"Embedding failed for source chunks: {', '.join(error_messages)}"
                    )

                embeddings = [
                    result.vector for result in embedding_results if result.vector is not None
                ]

            embedding_iter = iter(embeddings)
            db_chunks: list[SourceChunk] = []
            for chunk in chunks:
                embedding = chunk.embedding if chunk.embedding is not None else next(embedding_iter)
                db_chunks.append(
                    SourceChunk(
                        source_id=source_id,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        embedding=embedding,
                        meta=chunk.meta,
                    )
                )

            await self._repository.add_chunks(session, db_chunks)
            await session.commit()
            return db_chunks
        except Exception:
            await session.rollback()
            raise


def get_source_service() -> SourceService:
    """FastAPI dependency provider for SourceService."""
    return SourceService()
