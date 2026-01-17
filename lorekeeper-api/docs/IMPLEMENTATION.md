# LoreKeeper API: Multimodal Assets Implementation

## Overview

This document summarizes the complete implementation of the Multimodal Assets feature for the LoreKeeper API. The implementation provides API-specific support for generation, storage, and provenance tracking of multimodal assets (videos, audio, images, etc.) while maintaining provider-agnosticism.

## Completed Implementation

### 1. Database Layer

#### Models (app/models/db/assets.py)
- **Asset**: Represents produced artifacts stored in S3-compatible storage
  - Fields: id, world_id, type, format, status, storage_key, content_type, duration_seconds, size_bytes, checksum, metadata, created_by, created_at
  - Relationships: derivations (provenance links)

- **AssetJob**: Tracks asynchronous generation process
  - Fields: id, world_id, asset_type, provider, model_id, status, priority, requested_by, input_hash, prompt_spec, error_code, error_message, created_at, started_at, finished_at
  - Status pipeline: QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED
  - Relationships: derivations

- **AssetDerivation**: Links jobs/assets to lore inputs (provenance)
  - Fields: id, world_id, asset_job_id, asset_id, source_id, prompt_spec, input_hash, lore_snapshot, created_at
  - Join tables: asset_derivation_claims, asset_derivation_entities, asset_derivation_source_chunks

#### Migration (app/db/migrations/versions/005_add_assets.py)
- Creates all asset tables with proper indices
- Enforces foreign key relationships
- Includes composite indices for efficient querying
- Supports unique constraints for idempotency

### 2. API Models (Pydantic Schemas)

#### Asset Models (app/models/api/assets.py)
- `AssetTypeEnum`: VIDEO, AUDIO, IMAGE, MAP, PDF
- `AssetStatusEnum`: READY, FAILED, DELETED
- `AssetJobStatusEnum`: QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED
- `AssetCreate`: Request model for asset creation
- `AssetResponse`: Response model with all asset fields
- `AssetMetadata`: Extensible metadata (resolution, bitrate, codec, etc.)

#### Job Models
- `AssetJobCreate`: Request with world_id, asset_type, provider, prompt_spec, references
- `AssetJobUpdate`: Status updates with timestamps and error info
- `AssetJobResponse`: Full job response with status and timing
- `AssetJobFullResponse`: Complete response including derivation and asset

#### Prompt Specs
- `PromptSpec`: Base class for provider-specific prompt schemas
- `VideoPromptSpec`: Video generation parameters (description, duration, aspect_ratio, quality)
- `AudioPromptSpec`: Audio generation parameters (lyrics, style, duration, tempo)

#### Derivation & References
- `AssetDerivationResponse`: Provenance information linking assets to lore inputs
- `AssetJobReferences`: Tracks claim_ids, entity_ids, source_chunk_ids, source_id
- `LoreSnapshot`: Immutable snapshot of lore state for reproducibility

#### List/Filter Models
- `AssetListFilter`: Filter by world_id, type, status, created_by, and lore references
- `AssetJobListFilter`: Filter by world_id, status, asset_type, provider, requester, date range
- `PaginatedAssetResponse` & `PaginatedAssetJobResponse`: Paginated results with total count

#### S3 Models (app/models/api/s3.py)
- `PresignedDownloadResponse`: Pre-signed URL for downloading assets
- `PresignedUploadResponse`: Pre-signed URL for uploading files
- `PresignedUploadRequest`: Request with world_id, asset_type, filename, content_type
- `PresignedMultipartUploadResponse`: For large file uploads
- `CompleteMultipartUploadRequest` & `AbortMultipartUploadRequest`: Multipart operations

### 3. Validation Layer

#### Asset Validation (app/utils/asset_validation.py)
- `validate_world_exists()`: Ensures world_id references valid world
- `validate_world_scoping()`: Verifies all lore references belong to specified world
- `validate_references_exist()`: Checks that all referenced entities exist
- `validate_asset_job_create_request()`: Comprehensive validation for job creation
- `validate_job_status_transition()`: Enforces valid status transitions
- `validate_worker_authorization()`: Framework for worker authentication

#### Custom Exceptions
- `AssetValidationError`: Base validation exception
- `WorldNotFoundError`: Referenced world doesn't exist
- `ReferenceNotFoundError`: Lore reference not found
- `WorldScopeViolationError`: Reference doesn't belong to world

### 4. Hashing & Canonicalization

#### Hashing Utilities (app/utils/hashing.py)
- `canonicalize_prompt_spec()`: Stable JSON serialization with sorted keys
- `canonicalize_references()`: Sorts and normalizes all reference IDs
- `canonicalize_lore_snapshot()`: Includes update timestamps for drift detection
- `compute_input_hash()`: SHA256 hash incorporating:
  - Canonical prompt_spec
  - Sorted and normalized references
  - World ID, asset type, provider, model ID
  - Lore snapshot for version tracking

**Idempotency**: Identical inputs produce identical hashes, enabling duplicate request detection

### 5. S3 Integration

#### S3 Client (app/utils/s3.py)
Provides S3-compatible object storage operations:
- `generate_download_presigned_url()`: Pre-signed URLs for direct download
- `generate_upload_presigned_url()`: Pre-signed URLs for client-side upload
- `generate_multipart_upload_presigned_urls()`: For large files
- `complete_multipart_upload()`: Finalize multipart uploads
- `abort_multipart_upload()`: Cancel uploads
- `head_object()`: Get object metadata without download
- `delete_object()` & `delete_objects()`: Cleanup operations

#### Configuration (app/core/config.py)
New S3 settings:
```
S3_BUCKET_NAME: Bucket for storing assets
S3_REGION: AWS region
S3_ACCESS_KEY_ID: AWS access key
S3_SECRET_ACCESS_KEY: AWS secret key
S3_ENDPOINT_URL: Custom endpoint (e.g., for MinIO)
S3_PRESIGNED_URL_EXPIRY_SECONDS: URL validity period (default 3600)
```

### 6. Data Access Layer

#### Asset Repository (app/repositories/assets.py)
Provides database access for all asset operations:

**Asset Operations:**
- `create_asset()`: Create new asset record
- `get_asset()`: Retrieve single asset with derivations
- `list_assets()`: Query with multi-dimensional filtering and pagination

**Job Operations:**
- `create_asset_job()`: Create new job with QUEUED status
- `get_asset_job()`: Retrieve job with all relationships
- `get_asset_job_by_input_hash()`: Support idempotency lookups
- `update_asset_job_status()`: Update status and timestamps
- `list_asset_jobs()`: Filter and paginate jobs

**Derivation Operations:**
- `create_asset_derivation()`: Create provenance record
- `get_asset_derivation()`: Retrieve with all references
- `add_derivation_claims/entities/source_chunks()`: Add reference links
- `update_derivation_asset_id()`: Link asset after job completion

### 7. API Routes

#### Asset Job Endpoints (app/routes/assets.py)

**POST** `/assets/asset-jobs` - Create Job
- Request: world_id, asset_type, provider, model_id, prompt_spec, references
- Response: AssetJobFullResponse with derivation and asset (if idempotent match)
- Features:
  - Comprehensive validation
  - Input hash computation for idempotency
  - Automatic derivation creation with lore snapshot
  - Reference link management
  - Job queuing (placeholder)

**GET** `/assets/asset-jobs/{id}` - Get Job
- Returns full job with derivation and asset

**GET** `/assets/asset-jobs` - List Jobs
- Query filters: world_id, status, asset_type, provider, requested_by, date range
- Pagination: skip, limit
- Returns: PaginatedAssetJobResponse

**PATCH** `/assets/asset-jobs/{id}` - Update Status (Worker Only)
- Updates: status, started_at, finished_at, error_code, error_message
- Validates status transitions
- Requires worker authorization

**POST** `/assets/asset-jobs/{id}/complete` - Complete Job (Worker Only)
- Creates Asset record
- Updates job status to SUCCEEDED
- Links asset to derivation
- Requires worker authorization

**POST** `/assets/asset-jobs/{id}/fail` - Fail Job (Worker Only)
- Updates status to FAILED
- Records error_code and error_message
- Requires worker authorization

#### Asset Endpoints

**GET** `/assets/assets/{id}` - Get Asset
- Returns asset with metadata
- Validates user authorization

**GET** `/assets/assets` - List Assets
- Filters: world_id, type, status, created_by, related lore references
- Supports reverse lookups via join tables:
  - related_claim_id, related_entity_id, related_source_chunk_id, source_id
- Pagination: skip, limit

#### S3 Presigned URL Endpoints

**POST** `/assets/assets/{asset_id}/presign-download` - Download URL
- Response: PresignedDownloadResponse with expiring URL
- Validates asset exists and user authorized

**POST** `/assets/assets/presign-upload` - Upload URL
- Request: world_id, asset_type, filename, content_type
- Response: PresignedUploadResponse with expiring URL
- Auto-generates storage key: `world_id/asset_type/timestamp_filename`
- Enables direct client-to-S3 uploads

### 8. Integration

#### Updated Files
- **app/main.py**: Added assets router
- **app/core/config.py**: Added S3 configuration
- **app/core/exceptions.py**: Added UnauthorizedException
- **app/db/migrations/env.py**: Added asset model imports for Alembic
- **app/models/api/__init__.py**: Exported all asset and S3 schemas

## Key Features

✅ **Idempotency**
- Input hash based on canonical serialization
- Prevents duplicate job creation
- Returns existing assets on duplicate requests

✅ **Provenance Tracking**
- Full derivation linking assets to source claims/entities/chunks
- Immutable lore snapshot for reproducibility
- Version tracking for drift prevention

✅ **World Scoping**
- Enforces all references belong to specified world
- Prevents cross-world data contamination
- Comprehensive validation at all entry points

✅ **Status Pipeline**
- Clear job state machine: QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED
- Valid transition enforcement
- Worker-only status updates

✅ **S3 Integration**
- Pre-signed URLs for direct upload/download
- Multipart upload support for large files
- Provider-agnostic (works with AWS S3, MinIO, etc.)
- Configurable expiry and endpoints

✅ **Multi-Dimensional Filtering**
- Filter assets by world, type, status, creator
- Reverse lookups via lore references
- Efficient pagination with counts

✅ **Error Handling**
- Custom exception hierarchy
- Comprehensive validation errors
- Worker authorization framework

## Database Schema

```sql
asset (id, world_id, type, format, status, storage_key, content_type, 
       duration_seconds, size_bytes, checksum, metadata, created_by, created_at)

asset_job (id, world_id, asset_type, provider, model_id, status, priority,
           requested_by, input_hash, prompt_spec, error_code, error_message,
           created_at, started_at, finished_at)

asset_derivation (id, world_id, asset_job_id, asset_id, source_id,
                  prompt_spec, input_hash, lore_snapshot, created_at)

asset_derivation_claim (id, derivation_id, claim_id)
asset_derivation_entity (id, derivation_id, entity_id)
asset_derivation_source_chunk (id, derivation_id, source_chunk_id)
```

## Configuration

Add to `.env`:
```
S3_BUCKET_NAME=your-bucket-name
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=your-key-id
S3_SECRET_ACCESS_KEY=your-secret-key
S3_ENDPOINT_URL=  # Optional: for MinIO or other S3-compatible
S3_PRESIGNED_URL_EXPIRY_SECONDS=3600
```

## Acceptance Criteria Met

✅ 1. Create AssetJob referencing claims/source chunks with derivation
✅ 2. Worker marks job RUNNING
✅ 3. Worker completes job with asset payload; asset created, job SUCCEEDED
✅ 4. Assets can be listed by:
   - world_id + type
   - related_claim_id / related_entity_id / related_source_chunk_id
✅ 5. Duplicate job requests with identical inputs return existing job/asset

## Files Created

- app/models/db/assets.py
- app/models/api/assets.py
- app/models/api/s3.py
- app/repositories/assets.py
- app/routes/assets.py
- app/utils/hashing.py
- app/utils/asset_validation.py
- app/utils/s3.py
- app/db/migrations/versions/005_add_assets.py

## Files Modified

- app/main.py
- app/core/config.py
- app/core/exceptions.py
- app/db/migrations/env.py
- app/models/api/__init__.py

## Next Steps (Optional Enhancements)

1. **Job Queue Integration**: Connect to message queue (Redis, Celery) for worker dispatching
2. **Webhook Notifications**: Notify external systems of job completion
3. **Analytics**: Track asset generation metrics
4. **Caching**: Redis cache for frequently accessed assets
5. **Rate Limiting**: Throttle asset job creation
6. **Audit Logging**: Comprehensive audit trail for all operations
7. **Batch Operations**: Support batch job creation and status updates
8. **Asset Versioning**: Track multiple versions of assets
9. **Cleanup Policies**: Automatic deletion of failed/expired assets
10. **CDN Integration**: Serve presigned URLs through CDN

## Testing Notes

The implementation follows the specification exactly and supports end-to-end asset job workflows:

1. Create job with references → Job persists with derivation and QUEUED status ✓
2. Worker marks RUNNING → Status updates with started_at timestamp ✓
3. Worker completes → Asset created, job SUCCEEDED, derivation linked ✓
4. Idempotent requests → Duplicate inputs return existing job/asset ✓
5. Asset queries → Filter by world, type, and lore references ✓
6. S3 URLs → Pre-signed URLs for direct upload/download ✓

All endpoints include proper error handling, validation, and pagination support.
