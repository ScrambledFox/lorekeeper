"""OpenAI embedding provider implementation."""

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    BadRequestError,
    NotFoundError,
    OpenAI,
    RateLimitError,
)
from openai import AuthenticationError as OpenAIAuthenticationError

from app.types.embedding import (
    EmbeddingError,
    EmbeddingErrorCategory,
    EmbeddingUsage,
    ProviderEmbeddingResult,
)


class OpenAIEmbeddingProvider:
    """OpenAI embeddings provider."""

    name = "openai"

    def __init__(self, api_key: str, organization: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key, organization=organization)

    def embed(self, text: str, model_id: str, request_id: str | None) -> ProviderEmbeddingResult:
        return self.embed_batch([text], model_id, request_id=request_id)[0]

    def embed_batch(
        self, texts: list[str], model_id: str, request_id: str | None
    ) -> list[ProviderEmbeddingResult]:
        try:
            response = self._client.embeddings.create(
                model=model_id,
                input=texts,
                extra_headers=self._request_headers(request_id),
            )
        except Exception as exc:  # noqa: BLE001 - provider boundary
            error = self._classify_exception(exc)
            return [ProviderEmbeddingResult(vector=None, error=error) for _ in texts]

        usage_tokens = getattr(response.usage, "prompt_tokens", None) if response.usage else None
        results: list[ProviderEmbeddingResult] = []
        for idx, item in enumerate(response.data):
            results.append(
                ProviderEmbeddingResult(
                    vector=list(item.embedding),
                    usage=EmbeddingUsage(tokens=usage_tokens, chars=len(texts[idx])),
                )
            )
        return results

    @staticmethod
    def _request_headers(request_id: str | None) -> dict[str, str] | None:
        if not request_id:
            return None
        return {"X-Request-ID": request_id}

    @staticmethod
    def _classify_exception(exc: Exception) -> EmbeddingError:
        if isinstance(exc, RateLimitError):
            return EmbeddingError(
                category=EmbeddingErrorCategory.RATE_LIMIT,
                message=str(exc),
                retryable=True,
            )
        if isinstance(exc, APITimeoutError):
            return EmbeddingError(
                category=EmbeddingErrorCategory.TIMEOUT,
                message=str(exc),
                retryable=True,
            )
        if isinstance(exc, APIConnectionError):
            return EmbeddingError(
                category=EmbeddingErrorCategory.RETRYABLE,
                message=str(exc),
                retryable=True,
            )
        if isinstance(exc, OpenAIAuthenticationError):
            return EmbeddingError(
                category=EmbeddingErrorCategory.AUTH,
                message=str(exc),
                retryable=False,
            )
        if isinstance(exc, NotFoundError):
            return EmbeddingError(
                category=EmbeddingErrorCategory.MODEL_NOT_FOUND,
                message=str(exc),
                retryable=False,
            )
        if isinstance(exc, BadRequestError):
            return EmbeddingError(
                category=EmbeddingErrorCategory.INVALID_REQUEST,
                message=str(exc),
                retryable=False,
            )
        if isinstance(exc, APIStatusError):
            status_code = getattr(exc, "status_code", None)
            retryable = status_code is not None and status_code >= 500
            return EmbeddingError(
                category=EmbeddingErrorCategory.RETRYABLE
                if retryable
                else EmbeddingErrorCategory.NON_RETRYABLE,
                message=str(exc),
                retryable=retryable,
                provider_status=status_code,
            )
        return EmbeddingError(
            category=EmbeddingErrorCategory.NON_RETRYABLE,
            message=str(exc),
            retryable=False,
        )
