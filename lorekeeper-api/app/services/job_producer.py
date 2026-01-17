"""Job producer service for publishing asset generation tasks to the queue."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.assets import AssetJob, AssetJobStatus
from app.repositories.assets import AssetRepository
from app.services.job_queue import SQSJobQueue, get_job_queue
from app.types.job_queue import AssetGenerationPayload

logger = logging.getLogger(__name__)


class JobProducer:
    """Service for producing (publishing) jobs to the queue."""

    def __init__(self, queue: SQSJobQueue):
        """Initialize the job producer.

        Args:
            queue: SQS job queue instance
        """
        self.queue = queue

    async def publish_asset_job(
        self,
        asset_repo: AssetRepository,
        session: AsyncSession,
        asset_job: AssetJob,
        delay_seconds: int = 0,
    ) -> str:
        """Publish an asset job to the queue.

        This method:
        1. Validates the asset job
        2. Creates the job payload
        3. Publishes to SQS
        4. Updates the job status if needed

        Args:
            asset_repo: Asset repository for database operations
            session: Database session
            asset_job: The asset job to publish
            delay_seconds: Delay before message becomes visible

        Returns:
            Message ID from SQS

        Raises:
            ValueError: If job is invalid
            Exception: If queue operation fails
        """
        if not asset_job or not asset_job.id:
            raise ValueError("Invalid asset job")

        # Create the payload
        payload = AssetGenerationPayload(
            asset_job_id=asset_job.id,
            world_id=asset_job.world_id,
            asset_type=asset_job.asset_type,
            provider=asset_job.provider,
            model_id=asset_job.model_id,
            prompt_spec=asset_job.prompt_spec,
            priority=asset_job.priority,
            requested_by=asset_job.requested_by,
        )

        # Publish to queue
        message_id = await self.queue.enqueue_asset_job(
            job_id=str(asset_job.id),
            payload=payload,
            priority=asset_job.priority,
            delay_seconds=delay_seconds,
        )

        logger.info(
            f"Published asset job {asset_job.id} to queue (message_id={message_id}, "
            f"type={asset_job.asset_type}, provider={asset_job.provider})"
        )

        return message_id

    async def publish_asset_job_by_id(
        self,
        asset_repo: AssetRepository,
        session: AsyncSession,
        job_id: UUID,
        delay_seconds: int = 0,
    ) -> str:
        """Publish an asset job by ID to the queue.

        Args:
            asset_repo: Asset repository for database operations
            session: Database session
            job_id: ID of the asset job to publish
            delay_seconds: Delay before message becomes visible

        Returns:
            Message ID from SQS

        Raises:
            ValueError: If job not found or invalid
            Exception: If queue operation fails
        """
        asset_job = await asset_repo.get_asset_job(session, job_id)
        if not asset_job:
            raise ValueError(f"Asset job not found: {job_id}")

        return await self.publish_asset_job(
            asset_repo=asset_repo,
            session=session,
            asset_job=asset_job,
            delay_seconds=delay_seconds,
        )


async def get_job_producer() -> JobProducer:
    """Get a job producer instance.

    Returns:
        JobProducer instance with initialized queue

    Raises:
        Exception: If queue initialization fails
    """
    queue = await get_job_queue()
    return JobProducer(queue)
