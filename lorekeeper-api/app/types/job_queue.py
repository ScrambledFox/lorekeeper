"""Types and models for the job queue system."""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class JobType(str, Enum):
    """Enumeration of job types."""

    ASSET_GENERATION = "ASSET_GENERATION"


class JobStatus(str, Enum):
    """Job status enumeration."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AssetGenerationPayload(BaseModel):
    """Payload for asset generation jobs."""

    asset_job_id: UUID = Field(..., description="Asset job ID in database")
    world_id: UUID = Field(..., description="World ID")
    asset_type: str = Field(..., description="Asset type (VIDEO, AUDIO, IMAGE, MAP, PDF)")
    provider: str = Field(..., description="Generation provider")
    model_id: str | None = Field(None, description="Model ID on provider")
    prompt_spec: dict = Field(..., description="Provider-specific prompt spec")
    priority: int | None = Field(None, description="Job priority (higher = more urgent)")
    requested_by: str = Field(..., description="User who requested the job")


class QueuedMessage(BaseModel):
    """Message wrapper for queued jobs."""

    job_type: JobType = Field(..., description="Type of job")
    payload: dict = Field(..., description="Job-specific payload")
    message_id: str | None = Field(None, description="Queue message ID (assigned by queue)")
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum number of retries")


@dataclass
class ReceivedMessage:
    """Message received from the queue."""

    message_id: str
    body: str
    receipt_handle: str | None = None
    attempt_number: int = 1


class JobQueueError(Exception):
    """Base exception for job queue errors."""

    pass


class MessageNotFoundError(JobQueueError):
    """Raised when a message cannot be found in the queue."""

    pass


class QueueOperationError(JobQueueError):
    """Raised when a queue operation fails."""

    pass
