from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InternalServerErrorException, NotFoundException
from app.db.database import get_async_session
from app.models.api.books import BookCreate, BookResponse, BookVersionResponse, BookVersionUpdate
from app.models.db.books import Book, BookVersion, BookVersionStatus

book_router = APIRouter(prefix="/books")
book_versions_router = APIRouter(prefix="/book-versions")


@book_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_book(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    book: BookCreate,
):
    """Create a new book."""
    try:
        db_book = Book(
            world_id=book.world_id,
            title=book.title,
            author_ids=book.writer_ids,
            meta=book.meta,
        )

        session.add(db_book)
        await session.commit()
        await session.refresh(db_book)
        return db_book
    except NotFoundException:
        raise
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


@book_router.post("/{book_id}/versions/", status_code=status.HTTP_201_CREATED)
async def create_book_version(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    book_id: str,
):
    """Create a new version for a book."""
    try:
        book = await session.get(Book, book_id)
        if not book:
            raise NotFoundException(resource="Book", id=book_id)

        result = await session.execute(
            select(func.max(BookVersion.version_number)).where(BookVersion.book_id == book_id)
        )
        latest_version = result.scalar() or 0

        db_version = BookVersion(
            book_id=book_id, version_number=latest_version + 1, status=BookVersionStatus.DRAFT
        )

        session.add(db_version)
        await session.commit()
        await session.refresh(db_version)
        return db_version
    except NotFoundException:
        raise
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


@book_router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    book_id: str,
):
    """Retrieve a book by its ID."""
    try:
        result = await session.get(Book, book_id)
        if not result:
            raise NotFoundException(resource="Book", id=book_id)
        return result
    except NotFoundException:
        raise
    except Exception as e:
        raise InternalServerErrorException(message=str(e)) from e


@book_versions_router.patch("/{version_id}", response_model=BookVersionResponse)
async def update_book_version(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    version_id: str,
    version: BookVersionUpdate,
):
    """Update a book version. E.g. status updates from renderer."""
    try:
        db_version = await session.get(BookVersion, version_id)
        if not db_version:
            raise NotFoundException(resource="BookVersion", id=version_id)

        update_data = version.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_version, key, value)

        await session.commit()
        await session.refresh(db_version)
        return db_version
    except NotFoundException:
        raise
    except Exception as e:
        await session.rollback()
        raise InternalServerErrorException(message=str(e)) from e


router = APIRouter(tags=["books"])

router.include_router(book_router)
router.include_router(book_versions_router)
