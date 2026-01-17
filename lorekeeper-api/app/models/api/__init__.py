"""API models for request/response validation."""

from app.models.api.api import (
    ApiHealthResponse,
    ApiInfoResponse,
    ApiResponse,
    ApiStatusResponse,
    PaginationParams,
)
from app.models.api.books import (
    BookCreate,
    BookResponse,
    BookUpdate,
    BookVersionCreate,
    BookVersionResponse,
    BookVersionUpdate,
)
from app.models.api.claims import (
    ClaimCreate,
    ClaimEmbeddingCreate,
    ClaimEmbeddingResponse,
    ClaimEmbeddingUpdate,
    ClaimResponse,
    ClaimTagCreate,
    ClaimTagResponse,
    ClaimUpdate,
)
from app.models.api.common import TagCreate, TagResponse, TagUpdate
from app.models.api.entities import (
    EntityAliasCreate,
    EntityAliasResponse,
    EntityAliasUpdate,
    EntityCreate,
    EntityResponse,
    EntityTagCreate,
    EntityTagResponse,
    EntityUpdate,
)
from app.models.api.sources import (
    SourceChunkCreate,
    SourceChunkResponse,
    SourceChunkUpdate,
    SourceCreate,
    SourceResponse,
    SourceUpdate,
)
from app.models.api.worlds import WorldCreate, WorldMetadata, WorldResponse, WorldUpdate

__all__ = [
    # Generic API
    "ApiHealthResponse",
    "ApiInfoResponse",
    "ApiResponse",
    "ApiStatusResponse",
    "PaginationParams",
    # Common
    "TagResponse",
    "TagCreate",
    "TagUpdate",
    # Worlds
    "WorldResponse",
    "WorldCreate",
    "WorldUpdate",
    "WorldMetadata",
    # Books
    "BookResponse",
    "BookCreate",
    "BookUpdate",
    "BookVersionResponse",
    "BookVersionCreate",
    "BookVersionUpdate",
    # Sources
    "SourceResponse",
    "SourceCreate",
    "SourceUpdate",
    "SourceChunkResponse",
    "SourceChunkCreate",
    "SourceChunkUpdate",
    # Entities
    "EntityResponse",
    "EntityCreate",
    "EntityUpdate",
    "EntityAliasResponse",
    "EntityAliasCreate",
    "EntityAliasUpdate",
    "EntityTagResponse",
    "EntityTagCreate",
    # Claims
    "ClaimResponse",
    "ClaimCreate",
    "ClaimUpdate",
    "ClaimEmbeddingResponse",
    "ClaimEmbeddingCreate",
    "ClaimEmbeddingUpdate",
    "ClaimTagResponse",
    "ClaimTagCreate",
]
