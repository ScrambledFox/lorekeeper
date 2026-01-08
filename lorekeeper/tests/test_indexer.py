"""
Unit tests for document chunking and embedding services.
"""

import pytest

from lorekeeper.indexer.chunker import DocumentChunker, EmbeddingService


class TestDocumentChunker:
    """Tests for DocumentChunker class."""

    def test_chunker_initialization(self) -> None:
        """Test chunker can be initialized with default and custom parameters."""
        chunker = DocumentChunker()
        assert chunker.min_chunk_size == 300
        assert chunker.max_chunk_size == 800
        assert chunker.overlap_percentage == 0.15

        custom_chunker = DocumentChunker(min_chunk_size=100, max_chunk_size=500)
        assert custom_chunker.min_chunk_size == 100
        assert custom_chunker.max_chunk_size == 500

    def test_chunk_by_paragraphs(self) -> None:
        """Test paragraph-based chunking."""
        chunker = DocumentChunker()
        text = "First paragraph with some content.\n\nSecond paragraph also has content.\n\nThird paragraph."

        chunks = chunker.chunk_by_paragraphs(text)

        assert len(chunks) > 0
        for start, end, chunk_text in chunks:
            assert isinstance(start, int)
            assert isinstance(end, int)
            assert isinstance(chunk_text, str)
            assert end > start
            assert chunk_text in text

    def test_chunk_by_sentences(self) -> None:
        """Test sentence-based chunking."""
        chunker = DocumentChunker()
        text = "First sentence. Second sentence. Third sentence."

        chunks = chunker.chunk_by_sentences(text)

        assert len(chunks) > 0
        for start, end, chunk_text in chunks:
            assert isinstance(start, int)
            assert isinstance(end, int)
            assert isinstance(chunk_text, str)

    def test_chunk_prefers_paragraphs(self) -> None:
        """Test that chunking prefers paragraphs when available."""
        chunker = DocumentChunker()
        text_with_paragraphs = "Para 1.\n\nPara 2."
        text_with_sentences = "Sent 1. Sent 2."

        chunks_para = chunker.chunk(text_with_paragraphs, prefer_paragraphs=True)
        chunks_sent = chunker.chunk(text_with_sentences, prefer_paragraphs=True)

        # Both should return chunks
        assert len(chunks_para) > 0
        assert len(chunks_sent) > 0

    def test_chunk_positions_valid(self) -> None:
        """Test that chunk positions are valid."""
        chunker = DocumentChunker()
        text = "This is a longer text that spans multiple paragraphs.\n\nIt contains useful information.\n\nAnd more content."

        chunks = chunker.chunk(text)

        for start, end, chunk_text in chunks:
            # Verify positions match the text
            extracted = text[start:end]
            assert extracted == chunk_text

    def test_chunk_empty_text(self) -> None:
        """Test chunking empty text."""
        chunker = DocumentChunker()
        chunks = chunker.chunk("")
        assert len(chunks) == 0

    def test_chunk_single_paragraph(self) -> None:
        """Test chunking text with single paragraph."""
        chunker = DocumentChunker()
        text = "Single paragraph with content."
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1


class TestEmbeddingService:
    """Tests for EmbeddingService class."""

    def test_embedding_service_initialization(self) -> None:
        """Test embedding service can be initialized."""
        service = EmbeddingService(model_name="mock")
        assert service.model_name == "mock"
        assert service.embedding_dim == 1536

    def test_embedding_deterministic(self) -> None:
        """Test that embeddings are deterministic for the same input."""
        service = EmbeddingService(model_name="mock")
        text = "Test text for embedding"

        embedding1 = service.embed(text)
        embedding2 = service.embed(text)

        assert embedding1 == embedding2

    def test_embedding_dimensions(self) -> None:
        """Test that embeddings have correct dimensions."""
        service = EmbeddingService(model_name="mock")
        embedding = service.embed("Test text")

        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

    def test_embedding_normalized(self) -> None:
        """Test that embeddings are normalized (unit vectors)."""
        service = EmbeddingService(model_name="mock")
        embedding = service.embed("Test text")

        # Calculate magnitude
        magnitude = sum(x * x for x in embedding) ** 0.5

        # Should be close to 1.0 (normalized)
        assert abs(magnitude - 1.0) < 0.0001

    def test_embedding_different_texts(self) -> None:
        """Test that different texts produce different embeddings."""
        service = EmbeddingService(model_name="mock")

        embedding1 = service.embed("First text")
        embedding2 = service.embed("Second text")

        # Should be different
        assert embedding1 != embedding2

    def test_embedding_similar_texts(self) -> None:
        """Test that similar texts produce somewhat similar embeddings."""
        service = EmbeddingService(model_name="mock")

        embedding1 = service.embed("The king ruled the kingdom")
        embedding2 = service.embed("The king ruled the realm")

        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Similar texts should have positive correlation
        assert dot_product > 0

    def test_embedding_unsupported_model(self) -> None:
        """Test that unsupported models raise NotImplementedError."""
        service = EmbeddingService(model_name="unsupported_model")

        with pytest.raises(NotImplementedError):
            service.embed("Test text")
