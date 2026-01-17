"""Types and enums for embedding services."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class EmbeddingPurpose(str, Enum):
    """Logical purpose for embeddings."""

    CLAIM = "CLAIM"
    SOURCE_CHUNK = "SOURCE_CHUNK"
    ENTITY_SUMMARY = "ENTITY_SUMMARY"


class TruncateStrategy(str, Enum):
    """Text truncation strategy for over-length inputs."""

    END = "END"
    NONE = "NONE"
    ERROR = "ERROR"


class EmbeddingErrorCategory(str, Enum):
    """Error categories for embedding failures."""

    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTH = "AUTH"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"


@dataclass(frozen=True)
class EmbeddingUsage:
    """Usage stats returned from embedding providers."""

    tokens: int | None
    chars: int


@dataclass(frozen=True)
class EmbeddingError:
    """Structured embedding error information."""

    category: EmbeddingErrorCategory
    message: str
    retryable: bool
    provider_status: int | None = None


@dataclass(frozen=True)
class EmbeddingResult:
    """Result for a single embedding input."""

    vector: list[float] | None
    dimensions: int
    provider: str
    model_id: str
    wrapper_model_alias: str
    input_hash: str
    normalized_text_len: int
    usage: EmbeddingUsage
    latency_ms: float
    error: EmbeddingError | None = None


@dataclass(frozen=True)
class EmbeddingOptions:
    """Options for embedding requests."""

    model: str
    purpose: EmbeddingPurpose
    locale: str | None = None
    truncate_strategy: TruncateStrategy = TruncateStrategy.END
    request_id: str | None = None


@dataclass(frozen=True)
class EmbeddingModelConfig:
    """Configuration for an embedding model alias."""

    alias: str
    provider: str
    provider_model_id: str
    dimensions: int
    max_chars: int


@dataclass(frozen=True)
class ProviderEmbeddingResult:
    """Provider-specific embedding result."""

    vector: list[float] | None
    error: EmbeddingError | None = None
    usage: EmbeddingUsage | None = None


class EmbeddingProvider(Protocol):
    """Provider interface for embeddings."""

    name: str

    def embed(
        self, text: str, model_id: str, request_id: str | None
    ) -> ProviderEmbeddingResult: ...

    def embed_batch(
        self, texts: list[str], model_id: str, request_id: str | None
    ) -> list[ProviderEmbeddingResult]: ...
