"""Embedding service wrapper for provider-agnostic embeddings."""

from __future__ import annotations

import hashlib
import logging
import random
import time
from collections import OrderedDict

from app.types.embedding import (
    EmbeddingError,
    EmbeddingErrorCategory,
    EmbeddingModelConfig,
    EmbeddingOptions,
    EmbeddingProvider,
    EmbeddingResult,
    EmbeddingUsage,
    ProviderEmbeddingResult,
    TruncateStrategy,
)


class InMemoryEmbeddingCache:
    """Simple in-memory LRU cache for embeddings."""

    def __init__(self, max_entries: int = 2048) -> None:
        self.max_entries = max_entries
        self._cache: OrderedDict[tuple[str, str], EmbeddingResult] = OrderedDict()

    def get(self, model_alias: str, input_hash: str) -> EmbeddingResult | None:
        key = (model_alias, input_hash)
        value = self._cache.get(key)
        if value is None:
            return None
        self._cache.move_to_end(key)
        return value

    def set(self, model_alias: str, input_hash: str, value: EmbeddingResult) -> None:
        key = (model_alias, input_hash)
        self._cache[key] = value
        self._cache.move_to_end(key)
        if len(self._cache) > self.max_entries:
            self._cache.popitem(last=False)


class MockEmbeddingProvider:
    """Deterministic mock provider used for development/testing."""

    name = "mock"

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def embed(self, text: str, model_id: str, request_id: str | None) -> ProviderEmbeddingResult:
        return self.embed_batch([text], model_id, request_id=request_id)[0]

    def embed_batch(
        self, texts: list[str], model_id: str, request_id: str | None
    ) -> list[ProviderEmbeddingResult]:
        results: list[ProviderEmbeddingResult] = []
        for text in texts:
            vector = self._mock_embed(text)
            results.append(
                ProviderEmbeddingResult(
                    vector=vector,
                    usage=EmbeddingUsage(tokens=None, chars=len(text)),
                )
            )
        return results

    def _mock_embed(self, text: str) -> list[float]:
        text_hash = hashlib.sha256(text.encode()).digest()
        seed_values = [
            int.from_bytes(text_hash[i : i + 4], byteorder="big") for i in range(0, 32, 4)
        ]

        embedding: list[float] = []
        for i in range(self.dimensions):
            seed = seed_values[i % len(seed_values)] ^ (i * 2654435761)
            value = ((seed % 1000000) / 500000.0) - 1.0
            embedding.append(value)

        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


class EmbeddingServiceError(Exception):
    """Top-level error for embedding failures."""

    def __init__(self, error: EmbeddingError) -> None:
        super().__init__(error.message)
        self.error = error


class EmbeddingService:
    """Service for generating embeddings for text data."""

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        model_registry: dict[str, EmbeddingModelConfig] | None = None,
        cache: InMemoryEmbeddingCache | None = None,
        logger: logging.Logger | None = None,
        max_retries: int = 3,
        base_backoff_s: float = 0.3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_cooldown_s: float = 30.0,
    ) -> None:
        self._provider = provider or MockEmbeddingProvider()
        self._models = model_registry or {
            "claims_v1": EmbeddingModelConfig(
                alias="claims_v1",
                provider=self._provider.name,
                provider_model_id="mock-embedding-v1",
                dimensions=1536,
                max_chars=8000,
            ),
            "source_chunks_v1": EmbeddingModelConfig(
                alias="source_chunks_v1",
                provider=self._provider.name,
                provider_model_id="mock-embedding-v1",
                dimensions=1536,
                max_chars=12000,
            ),
        }
        self._cache = cache or InMemoryEmbeddingCache()
        self._logger = logger or logging.getLogger(__name__)
        self._max_retries = max_retries
        self._base_backoff_s = base_backoff_s
        self._circuit_breaker_threshold = circuit_breaker_threshold
        self._circuit_breaker_cooldown_s = circuit_breaker_cooldown_s
        self._consecutive_failures = 0
        self._last_failure_ts: float | None = None

        self._metrics: dict[str, int] = {
            "requests": 0,
            "cache_hits": 0,
            "retries": 0,
            "errors": 0,
        }

    def embed(self, text: str, opts: EmbeddingOptions) -> EmbeddingResult:
        """Embed a single text input."""
        results = self.embed_batch([text], opts)
        result = results[0]
        if result.error is not None:
            raise EmbeddingServiceError(result.error)
        return result

    def embed_batch(self, texts: list[str], opts: EmbeddingOptions) -> list[EmbeddingResult]:
        """Embed a batch of text inputs."""
        self._metrics["requests"] += len(texts)
        if not texts:
            return []

        model_config = self._get_model_config(opts.model)
        if self._is_circuit_open():
            error = EmbeddingError(
                category=EmbeddingErrorCategory.CIRCUIT_OPEN,
                message="Embedding provider circuit is open",
                retryable=True,
            )
            return [self._error_result(text, opts, model_config, error) for text in texts]

        normalized_texts, results = self._prepare_normalized_results(texts, opts, model_config)
        self._process_cache_and_requests(normalized_texts, results, opts, model_config)
        return results

    def _prepare_normalized_results(
        self,
        texts: list[str],
        opts: EmbeddingOptions,
        model_config: EmbeddingModelConfig,
    ) -> tuple[list[str], list[EmbeddingResult]]:
        """Normalize texts and prepare initial results with truncation errors."""
        normalized_texts: list[str] = []
        truncated_errors: list[EmbeddingError | None] = []
        for text in texts:
            normalized = self._normalize_text(text)
            normalized, error = self._apply_truncate_strategy(normalized, opts, model_config)
            normalized_texts.append(normalized)
            truncated_errors.append(error)

        results: list[EmbeddingResult] = [
            self._error_result(text, opts, model_config, error)
            if error
            else self._placeholder_result(normalized, opts, model_config)
            for text, normalized, error in zip(
                texts, normalized_texts, truncated_errors, strict=True
            )
        ]
        return normalized_texts, results

    def _process_cache_and_requests(
        self,
        normalized_texts: list[str],
        results: list[EmbeddingResult],
        opts: EmbeddingOptions,
        model_config: EmbeddingModelConfig,
    ) -> None:
        """Process cache lookups and handle provider requests for uncached items."""
        cache_hits: dict[int, EmbeddingResult] = {}
        to_request: list[str] = []
        to_request_indices: list[int] = []

        for idx, normalized in enumerate(normalized_texts):
            if results[idx].error is not None:
                continue
            input_hash = self._hash_input(model_config.provider_model_id, normalized)
            cached = self._cache.get(model_config.alias, input_hash)
            if cached is not None:
                cache_hits[idx] = cached
                self._metrics["cache_hits"] += 1
            else:
                to_request.append(normalized)
                to_request_indices.append(idx)

        for idx, cached in cache_hits.items():
            results[idx] = cached

        if to_request:
            provider_results = self._embed_with_retries(to_request, model_config, opts)
            for idx, provider_result in zip(to_request_indices, provider_results, strict=True):
                normalized = normalized_texts[idx]
                input_hash = self._hash_input(model_config.provider_model_id, normalized)
                result = self._provider_result_to_embedding(
                    provider_result,
                    opts,
                    model_config,
                    input_hash,
                    normalized,
                )
                results[idx] = result
                if result.error is None:
                    self._cache.set(model_config.alias, input_hash, result)

    def metrics_snapshot(self) -> dict[str, int]:
        """Return a snapshot of in-memory metrics counters."""
        return dict(self._metrics)

    def _get_model_config(self, alias: str) -> EmbeddingModelConfig:
        config = self._models.get(alias)
        if config is None:
            raise EmbeddingServiceError(
                EmbeddingError(
                    category=EmbeddingErrorCategory.MODEL_NOT_FOUND,
                    message=f"Embedding model alias '{alias}' not found",
                    retryable=False,
                )
            )
        return config

    def _normalize_text(self, text: str) -> str:
        stripped = text.strip()
        cleaned = "".join(ch for ch in stripped if ch.isprintable())
        normalized = " ".join(cleaned.split())
        return normalized

    def _apply_truncate_strategy(
        self, text: str, opts: EmbeddingOptions, model_config: EmbeddingModelConfig
    ) -> tuple[str, EmbeddingError | None]:
        if len(text) <= model_config.max_chars:
            return text, None

        if opts.truncate_strategy == TruncateStrategy.NONE:
            return text, None
        if opts.truncate_strategy == TruncateStrategy.ERROR:
            return text, EmbeddingError(
                category=EmbeddingErrorCategory.INVALID_REQUEST,
                message="Input text exceeds maximum length",
                retryable=False,
            )
        return text[: model_config.max_chars], None

    def _hash_input(self, model_id: str, text: str) -> str:
        hash_source = f"{model_id}:{text}".encode()
        return hashlib.sha256(hash_source).hexdigest()

    def _embed_with_retries(
        self, texts: list[str], model_config: EmbeddingModelConfig, opts: EmbeddingOptions
    ) -> list[ProviderEmbeddingResult]:
        attempt = 0
        while True:
            attempt += 1
            start = time.monotonic()
            try:
                provider_results = self._provider.embed_batch(
                    texts,
                    model_config.provider_model_id,
                    request_id=opts.request_id,
                )
                latency_ms = (time.monotonic() - start) * 1000
                self._log_success(opts, model_config, len(texts), latency_ms)
                self._reset_circuit()
                return provider_results
            except Exception as exc:  # noqa: BLE001 - intentional broad catch
                error = self._classify_exception(exc)
                self._metrics["errors"] += 1
                self._record_failure()
                self._log_error(opts, model_config, len(texts), error)
                if not error.retryable or attempt > self._max_retries:
                    return [ProviderEmbeddingResult(vector=None, error=error) for _ in texts]
                self._metrics["retries"] += 1
                time.sleep(self._backoff_delay(attempt))

    def _provider_result_to_embedding(
        self,
        provider_result: ProviderEmbeddingResult,
        opts: EmbeddingOptions,
        model_config: EmbeddingModelConfig,
        input_hash: str,
        normalized_text: str,
    ) -> EmbeddingResult:
        usage = provider_result.usage or EmbeddingUsage(tokens=None, chars=len(normalized_text))
        latency_ms = 0.0
        if provider_result.error is not None:
            self._metrics["errors"] += 1
            return EmbeddingResult(
                vector=None,
                dimensions=model_config.dimensions,
                provider=model_config.provider,
                model_id=model_config.provider_model_id,
                wrapper_model_alias=model_config.alias,
                input_hash=input_hash,
                normalized_text_len=len(normalized_text),
                usage=usage,
                latency_ms=latency_ms,
                error=provider_result.error,
            )
        return EmbeddingResult(
            vector=provider_result.vector,
            dimensions=model_config.dimensions,
            provider=model_config.provider,
            model_id=model_config.provider_model_id,
            wrapper_model_alias=model_config.alias,
            input_hash=input_hash,
            normalized_text_len=len(normalized_text),
            usage=usage,
            latency_ms=latency_ms,
            error=None,
        )

    def _placeholder_result(
        self, normalized_text: str, opts: EmbeddingOptions, model_config: EmbeddingModelConfig
    ) -> EmbeddingResult:
        return EmbeddingResult(
            vector=None,
            dimensions=model_config.dimensions,
            provider=model_config.provider,
            model_id=model_config.provider_model_id,
            wrapper_model_alias=model_config.alias,
            input_hash=self._hash_input(model_config.provider_model_id, normalized_text),
            normalized_text_len=len(normalized_text),
            usage=EmbeddingUsage(tokens=None, chars=len(normalized_text)),
            latency_ms=0.0,
            error=None,
        )

    def _error_result(
        self,
        text: str,
        opts: EmbeddingOptions,
        model_config: EmbeddingModelConfig,
        error: EmbeddingError,
    ) -> EmbeddingResult:
        normalized = self._normalize_text(text)
        return EmbeddingResult(
            vector=None,
            dimensions=model_config.dimensions,
            provider=model_config.provider,
            model_id=model_config.provider_model_id,
            wrapper_model_alias=model_config.alias,
            input_hash=self._hash_input(model_config.provider_model_id, normalized),
            normalized_text_len=len(normalized),
            usage=EmbeddingUsage(tokens=None, chars=len(normalized)),
            latency_ms=0.0,
            error=error,
        )

    def _classify_exception(self, exc: Exception) -> EmbeddingError:
        message = str(exc)
        if "timeout" in message.lower():
            return EmbeddingError(
                category=EmbeddingErrorCategory.TIMEOUT,
                message=message,
                retryable=True,
            )
        if "rate" in message.lower():
            return EmbeddingError(
                category=EmbeddingErrorCategory.RATE_LIMIT,
                message=message,
                retryable=True,
            )
        return EmbeddingError(
            category=EmbeddingErrorCategory.RETRYABLE,
            message=message,
            retryable=True,
        )

    def _backoff_delay(self, attempt: int) -> float:
        jitter = random.uniform(0.8, 1.2)
        return self._base_backoff_s * (2 ** (attempt - 1)) * jitter

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        self._last_failure_ts = time.monotonic()

    def _reset_circuit(self) -> None:
        self._consecutive_failures = 0
        self._last_failure_ts = None

    def _is_circuit_open(self) -> bool:
        if self._consecutive_failures < self._circuit_breaker_threshold:
            return False
        if self._last_failure_ts is None:
            return True
        return (time.monotonic() - self._last_failure_ts) < self._circuit_breaker_cooldown_s

    def _log_success(
        self,
        opts: EmbeddingOptions,
        model_config: EmbeddingModelConfig,
        batch_size: int,
        latency_ms: float,
    ) -> None:
        self._logger.info(
            "embedding.batch.success",
            extra={
                "request_id": opts.request_id,
                "purpose": opts.purpose.value,
                "model_alias": model_config.alias,
                "provider": model_config.provider,
                "provider_model_id": model_config.provider_model_id,
                "batch_size": batch_size,
                "latency_ms": latency_ms,
            },
        )

    def _log_error(
        self,
        opts: EmbeddingOptions,
        model_config: EmbeddingModelConfig,
        batch_size: int,
        error: EmbeddingError,
    ) -> None:
        self._logger.warning(
            "embedding.batch.error",
            extra={
                "request_id": opts.request_id,
                "purpose": opts.purpose.value,
                "model_alias": model_config.alias,
                "provider": model_config.provider,
                "provider_model_id": model_config.provider_model_id,
                "batch_size": batch_size,
                "error_category": error.category.value,
                "error_message": error.message,
            },
        )
