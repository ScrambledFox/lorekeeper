"""
Document API routes for LoreKeeper.
"""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from lorekeeper.api.schemas import (
    DocumentCreate,
    DocumentIndexRequest,
    DocumentIndexResponse,
    DocumentResponse,
    DocumentSearchResult,
)
from lorekeeper.db.database import get_async_session
from lorekeeper.db.models import Document, DocumentSnippet
from lorekeeper.indexer.chunker import DocumentChunker, EmbeddingService

router = APIRouter(prefix="/worlds/{world_id}/documents", tags=["documents"])

# Initialize services
chunker = DocumentChunker()
embedding_service = EmbeddingService(model_name="mock")


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    world_id: UUID,
    document: DocumentCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DocumentResponse:
    """Create a new document in a world."""
    try:
        db_document = Document(
            world_id=world_id,
            mode=document.mode,
            kind=document.kind,
            title=document.title,
            author=document.author,
            in_world_date=document.in_world_date,
            text=document.text,
            provenance=document.provenance,
        )
        session.add(db_document)
        await session.commit()
        await session.refresh(db_document)
        return DocumentResponse.model_validate(db_document, from_attributes=True)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    world_id: UUID,
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DocumentResponse:
    """Get a document by ID."""
    result = await session.execute(
        select(Document).where(and_(Document.id == document_id, Document.world_id == world_id))
    )
    db_document = result.scalars().first()

    if not db_document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return DocumentResponse.model_validate(db_document, from_attributes=True)


@router.post("/{document_id}/index", response_model=DocumentIndexResponse)
async def index_document(
    world_id: UUID,
    document_id: UUID,
    config: DocumentIndexRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> DocumentIndexResponse:
    """
    Index a document by chunking and embedding it.

    This creates snippets from the document text and generates embeddings for each snippet.
    """
    # Get the document
    result = await session.execute(
        select(Document).where(and_(Document.id == document_id, Document.world_id == world_id))
    )
    db_document = result.scalars().first()

    if not db_document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        # Chunk the document
        chunker_local = DocumentChunker(
            min_chunk_size=config.chunk_size_min,
            max_chunk_size=config.chunk_size_max,
            overlap_percentage=config.overlap_percentage,
        )
        chunks = chunker_local.chunk(db_document.text)

        # Create snippets with embeddings
        snippet_ids: list[UUID] = []
        for index, (start_char, end_char, chunk_text) in enumerate(chunks):
            # Generate embedding
            embedding = embedding_service.embed(chunk_text)

            snippet = DocumentSnippet(
                id=uuid4(),
                document_id=document_id,
                world_id=world_id,
                snippet_index=index,
                start_char=start_char,
                end_char=end_char,
                snippet_text=chunk_text,
                embedding=embedding,
            )
            session.add(snippet)
            snippet_ids.append(snippet.id)

        await session.commit()

        return DocumentIndexResponse(
            document_id=document_id,
            snippets_created=len(chunks),
            snippet_ids=snippet_ids,
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/search", response_model=DocumentSearchResult)
async def search_documents(
    world_id: UUID,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    query: str | None = Query(None, description="Search query in title/author"),
    mode: str | None = Query(None, description="Filter by mode (STRICT or MYTHIC)"),
    kind: str | None = Query(None, description="Filter by document kind"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> DocumentSearchResult:
    """Search documents by title, author, or filters."""
    # Build query
    q = select(Document).where(Document.world_id == world_id)

    if query:
        # Search by title or author
        search_term = f"%{query}%"
        from sqlalchemy import or_

        q = q.where(
            or_(
                Document.title.ilike(search_term),
                Document.author.ilike(search_term),
            )
        )

    if mode:
        q = q.where(Document.mode == mode)

    if kind:
        q = q.where(Document.kind == kind)

    # Get total count
    count_query = select(func.count()).select_from(Document).where(Document.world_id == world_id)
    if query:
        from sqlalchemy import or_

        search_term = f"%{query}%"
        count_query = count_query.where(
            or_(
                Document.title.ilike(search_term),
                Document.author.ilike(search_term),
            )
        )
    if mode:
        count_query = count_query.where(Document.mode == mode)
    if kind:
        count_query = count_query.where(Document.kind == kind)

    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    q = q.offset(offset).limit(limit)
    result = await session.execute(q)
    documents = result.scalars().all()

    return DocumentSearchResult(
        total=total,
        results=[DocumentResponse.model_validate(d, from_attributes=True) for d in documents],
    )
