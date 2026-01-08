"""
Document indexing and embedding module for LoreKeeper.
"""

import hashlib
from typing import Optional


class DocumentChunker:
    """Chunk documents into snippets with proper typing."""

    def __init__(
        self,
        min_chunk_size: int = 300,
        max_chunk_size: int = 800,
        overlap_percentage: float = 0.15,
    ) -> None:
        """
        Initialize document chunker.

        Args:
            min_chunk_size: Minimum tokens per chunk
            max_chunk_size: Maximum tokens per chunk
            overlap_percentage: Percentage of overlap between chunks (0-1)
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_percentage = overlap_percentage

    def chunk_by_paragraphs(self, text: str) -> list[tuple[int, int, str]]:
        """
        Chunk text by paragraphs.

        Args:
            text: Text to chunk

        Returns:
            List of tuples: (start_char, end_char, chunk_text)
        """
        chunks: list[tuple[int, int, str]] = []
        paragraphs: list[str] = text.split("\n\n")
        current_chunk: str = ""
        chunk_start: int = 0

        for para in paragraphs:
            if not para.strip():
                continue

            # Check if adding paragraph would exceed max size
            potential_chunk: str = f"{current_chunk}\n\n{para}" if current_chunk else para
            potential_tokens: int = len(potential_chunk.split())

            if potential_tokens > self.max_chunk_size and current_chunk:
                # Save current chunk and start new one
                chunk_end: int = text.find(current_chunk) + len(current_chunk)
                chunks.append((chunk_start, chunk_end, current_chunk))
                current_chunk = para
                chunk_start = text.find(para)
            else:
                current_chunk = potential_chunk

        # Save final chunk
        if current_chunk:
            chunk_end = text.find(current_chunk) + len(current_chunk)
            chunks.append((chunk_start, chunk_end, current_chunk))

        return chunks

    def chunk_by_sentences(self, text: str) -> list[tuple[int, int, str]]:
        """
        Chunk text by sentences.

        Args:
            text: Text to chunk

        Returns:
            List of tuples: (start_char, end_char, chunk_text)
        """
        chunks: list[tuple[int, int, str]] = []
        sentences: list[str] = text.split(". ")
        current_chunk: str = ""
        chunk_start: int = 0

        for sentence in sentences:
            if not sentence.strip():
                continue

            sentence_clean: str = sentence if sentence.endswith(".") else f"{sentence}."
            potential_chunk: str = (
                f"{current_chunk} {sentence_clean}" if current_chunk else sentence_clean
            )
            potential_tokens: int = len(potential_chunk.split())

            if potential_tokens > self.max_chunk_size and current_chunk:
                # Save current chunk and start new one
                chunk_end: int = text.find(current_chunk) + len(current_chunk)
                chunks.append((chunk_start, chunk_end, current_chunk))
                current_chunk = sentence_clean
                chunk_start = text.find(sentence_clean)
            else:
                current_chunk = potential_chunk

        # Save final chunk
        if current_chunk:
            chunk_end = text.find(current_chunk) + len(current_chunk)
            chunks.append((chunk_start, chunk_end, current_chunk))

        return chunks

    def chunk(self, text: str, prefer_paragraphs: bool = True) -> list[tuple[int, int, str]]:
        """
        Chunk text intelligently.

        Args:
            text: Text to chunk
            prefer_paragraphs: If True, prefer paragraph-based chunking

        Returns:
            List of tuples: (start_char, end_char, chunk_text)
        """
        if prefer_paragraphs and "\n\n" in text:
            return self.chunk_by_paragraphs(text)
        else:
            return self.chunk_by_sentences(text)


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self, model_name: str = "mock") -> None:
        """
        Initialize embedding service.

        Args:
            model_name: Name of the embedding model. For Phase 1, use "mock" for deterministic embeddings.
        """
        self.model_name = model_name
        self.embedding_dim = 1536

    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector (1536 dimensions)

        Note:
            For Phase 1, this uses a deterministic mock implementation based on text hash.
            In Phase 2, this will be replaced with actual embedding models (e.g., OpenAI, Hugging Face).
        """
        if self.model_name == "mock":
            return self._mock_embed(text)
        else:
            raise NotImplementedError(f"Model {self.model_name} not implemented yet")

    def _mock_embed(self, text: str) -> list[float]:
        """
        Generate deterministic mock embeddings based on text hash.

        Args:
            text: Text to embed

        Returns:
            Deterministic 1536-dimensional embedding vector
        """
        # Create a deterministic seed from text hash
        text_hash = hashlib.sha256(text.encode()).digest()
        seed_values = [
            int.from_bytes(text_hash[i : i + 4], byteorder="big") for i in range(0, 32, 4)
        ]

        # Generate embedding using seeded pseudo-random values
        embedding: list[float] = []
        for i in range(self.embedding_dim):
            seed = seed_values[i % len(seed_values)] ^ (i * 2654435761)  # Mix in index
            # Use deterministic values scaled to [-1, 1]
            value = ((seed % 1000000) / 500000.0) - 1.0
            embedding.append(value)

        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding
