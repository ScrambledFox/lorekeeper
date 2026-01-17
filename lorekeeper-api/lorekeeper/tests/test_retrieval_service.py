"""
Tests for the retrieval service.
"""

from lorekeeper.services.retrieval import RetrievalService


class TestRetrievalService:
    """Tests for RetrievalService class."""

    def test_cosine_similarity_identical_vectors(self) -> None:
        """Test cosine similarity of identical vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = RetrievalService.cosine_similarity(vec1, vec2)

        assert similarity == 1.0

    def test_cosine_similarity_orthogonal_vectors(self) -> None:
        """Test cosine similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        similarity = RetrievalService.cosine_similarity(vec1, vec2)

        assert similarity == 0.0

    def test_cosine_similarity_opposite_vectors(self) -> None:
        """Test cosine similarity of opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]

        similarity = RetrievalService.cosine_similarity(vec1, vec2)

        assert similarity == -1.0

    def test_cosine_similarity_similar_vectors(self) -> None:
        """Test cosine similarity of similar vectors."""
        vec1 = [1.0, 1.0, 0.0]
        vec2 = [1.0, 1.0, 0.0]

        similarity = RetrievalService.cosine_similarity(vec1, vec2)

        assert abs(similarity - 1.0) < 0.0001

    def test_cosine_similarity_empty_vectors(self) -> None:
        """Test cosine similarity with empty vectors."""
        similarity = RetrievalService.cosine_similarity([], [])
        assert similarity == 0.0

    def test_cosine_similarity_zero_magnitude(self) -> None:
        """Test cosine similarity when magnitude is zero."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = RetrievalService.cosine_similarity(vec1, vec2)

        assert similarity == 0.0

    def test_cosine_similarity_different_lengths(self) -> None:
        """Test cosine similarity with different vector lengths."""
        vec1 = [1.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = RetrievalService.cosine_similarity(vec1, vec2)

        assert similarity == 0.0

    def test_cosine_similarity_numpy_like_arrays(self) -> None:
        """Test cosine similarity with numpy-like arrays."""

        # Simulate numpy array-like objects with tolist method
        class ArrayLike:
            def __init__(self, data: list[float]):
                self.data = data

            def tolist(self) -> list[float]:
                return self.data

        vec1 = ArrayLike([1.0, 0.0, 0.0])
        vec2 = ArrayLike([1.0, 0.0, 0.0])

        similarity = RetrievalService.cosine_similarity(vec1, vec2)

        assert similarity == 1.0

    def test_cosine_similarity_partial_overlap(self) -> None:
        """Test cosine similarity with partially overlapping vectors."""
        vec1 = [1.0, 1.0, 0.0]
        vec2 = [1.0, 0.0, 1.0]

        # Both have magnitude sqrt(2)
        # dot product = 1*1 + 1*0 + 0*1 = 1
        # similarity = 1 / (sqrt(2) * sqrt(2)) = 1/2 = 0.5
        similarity = RetrievalService.cosine_similarity(vec1, vec2)

        assert abs(similarity - 0.5) < 0.0001
