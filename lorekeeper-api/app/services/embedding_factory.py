"""Factory for configured EmbeddingService instances."""

from app.core.config import settings
from app.services.embedding import EmbeddingService
from app.services.embedding_providers.openai import OpenAIEmbeddingProvider
from app.types.embedding import EmbeddingModelConfig


def get_embedding_service() -> EmbeddingService:
    """Create an EmbeddingService based on environment configuration."""
    provider_name = settings.EMBEDDING_PROVIDER.lower()

    if provider_name != "openai":
        return EmbeddingService()

    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")

    organization = settings.OPENAI_ORGANIZATION
    provider = OpenAIEmbeddingProvider(api_key=api_key, organization=organization)

    model_id = settings.OPENAI_EMBEDDING_MODEL_ID or "text-embedding-3-small"
    dimensions = int(settings.OPENAI_EMBEDDING_DIMENSIONS or "1536")

    model_registry = {
        "claims_v1": EmbeddingModelConfig(
            alias="claims_v1",
            provider=provider.name,
            provider_model_id=model_id,
            dimensions=dimensions,
            max_chars=8000,
        ),
        "source_chunks_v1": EmbeddingModelConfig(
            alias="source_chunks_v1",
            provider=provider.name,
            provider_model_id=model_id,
            dimensions=dimensions,
            max_chars=12000,
        ),
    }

    return EmbeddingService(provider=provider, model_registry=model_registry)
