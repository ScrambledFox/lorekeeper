"""
Test module to verify typing implementation.
"""

from typing import Any
from uuid import UUID

import pytest

from lorekeeper.indexer.chunker import DocumentChunker, EmbeddingService
from lorekeeper.models.api.common import ApiResponse, PaginationParams
from lorekeeper.utils.ids import format_uuid, parse_uuid


def test_document_chunker_by_paragraphs() -> None:
    """Test document chunking by paragraphs."""
    chunker: DocumentChunker = DocumentChunker()
    text: str = "This is paragraph one.\n\nThis is paragraph two.\n\nThis is paragraph three."

    chunks: list[tuple[int, int, str]] = chunker.chunk(text, prefer_paragraphs=True)

    assert len(chunks) > 0
    for start, end, chunk_text in chunks:
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert isinstance(chunk_text, str)
        assert len(chunk_text) > 0


def test_api_response() -> None:
    """Test ApiResponse typing."""
    response: ApiResponse[dict[str, str]] = ApiResponse(
        data={"key": "value"}, success=True, message="Success"
    )

    result: dict[str, Any] = response.to_dict()
    assert result["success"] is True
    assert result["data"] == {"key": "value"}
    assert result["message"] == "Success"


def test_pagination_params() -> None:
    """Test PaginationParams typing."""
    params: PaginationParams = PaginationParams(page=2, page_size=50)

    assert params.page == 2
    assert params.page_size == 50
    assert params.skip == 50

    params_dict: dict[str, int] = params.to_dict()
    assert params_dict["page"] == 2
    assert params_dict["page_size"] == 50


def test_uuid_utilities() -> None:
    """Test UUID utility functions."""
    test_uuid: UUID = UUID("550e8400-e29b-41d4-a716-446655440000")

    formatted: str = format_uuid(test_uuid)
    assert isinstance(formatted, str)
    assert formatted == "550e8400-e29b-41d4-a716-446655440000"

    parsed: UUID = parse_uuid(formatted)
    assert parsed == test_uuid

    with pytest.raises(ValueError):
        parse_uuid("not-a-uuid")


def test_embedding_service() -> None:
    """Test EmbeddingService typing."""
    embedder: EmbeddingService = EmbeddingService(model_name="mock")

    embedding: list[float] = embedder.embed("test text")
    assert isinstance(embedding, list)
    assert len(embedding) == 1536
    assert all(isinstance(x, float) for x in embedding)

    # Test determinism
    embedding2: list[float] = embedder.embed("test text")
    assert embedding == embedding2
