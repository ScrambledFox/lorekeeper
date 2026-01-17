"""Example worker implementation for processing asset generation jobs."""

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.assets import AssetJobStatus
from app.repositories.assets import AssetRepository
from app.services.job_consumer import JobConsumer
from app.types.job_queue import AssetGenerationPayload

logger = logging.getLogger(__name__)


class AssetGenerationWorker:
    """Worker for handling asset generation jobs."""

    def __init__(self, consumer: JobConsumer, asset_repo: AssetRepository):
        """Initialize the asset generation worker.

        Args:
            consumer: Job consumer instance
            asset_repo: Asset repository
        """
        self.consumer = consumer
        self.asset_repo = asset_repo

    async def handle_asset_generation(
        self, payload: AssetGenerationPayload, session: AsyncSession
    ) -> None:
        """Handle an asset generation job.

        This is a mock implementation that simulates the asset generation process.
        In production, this would call actual generation providers (Sora, etc).

        Args:
            payload: Asset generation payload
            session: Database session
        """
        logger.info(
            f"Processing asset job {payload.asset_job_id}: "
            f"type={payload.asset_type}, provider={payload.provider}"
        )

        try:
            # Update job status to RUNNING
            await self.asset_repo.update_asset_job_status(
                session=session,
                asset_job_id=payload.asset_job_id,
                status=AssetJobStatus.RUNNING,
                started_at=datetime.utcnow(),
            )
            await session.commit()

            # TODO: Call actual generation provider
            # For now, simulate with a delay
            logger.info(f"Simulating asset generation for {payload.asset_type}...")
            await asyncio.sleep(5)

            # Update job status to SUCCEEDED
            await self.asset_repo.update_asset_job_status(
                session=session,
                asset_job_id=payload.asset_job_id,
                status=AssetJobStatus.SUCCEEDED,
                finished_at=datetime.utcnow(),
            )
            await session.commit()

            logger.info(f"Successfully completed asset job {payload.asset_job_id}")

        except Exception as e:
            logger.error(f"Error processing asset job {payload.asset_job_id}: {e}", exc_info=True)

            # Update job status to FAILED
            try:
                await self.asset_repo.update_asset_job_status(
                    session=session,
                    asset_job_id=payload.asset_job_id,
                    status=AssetJobStatus.FAILED,
                    finished_at=datetime.utcnow(),
                    error_code="GENERATION_ERROR",
                    error_message=str(e),
                )
                await session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}", exc_info=True)


async def create_and_run_worker(async_session_maker) -> None:
    """Create and run the asset generation worker.

    This is an example of how to set up and run a worker process.

    Args:
        async_session_maker: SQLAlchemy async session factory
    """
    from app.services.job_consumer import JobConsumer
    from app.types.job_queue import JobType

    # Create consumer
    consumer = JobConsumer(
        queue=None,  # Will be initialized by get_job_consumer
        async_session_maker=async_session_maker,
    )

    # Initialize the queue
    from app.services.job_queue import get_job_queue

    queue = await get_job_queue()
    consumer.queue = queue

    # Create worker
    asset_repo = AssetRepository()
    worker = AssetGenerationWorker(consumer, asset_repo)

    # Register handler
    async def handle_asset_job(payload: AssetGenerationPayload) -> None:
        async with async_session_maker() as session:
            await worker.handle_asset_generation(payload, session)

    consumer.register_handler(JobType.ASSET_GENERATION, handle_asset_job)

    # Run consumer
    try:
        await consumer.run(max_messages=1, wait_time_seconds=20)
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
    finally:
        from app.services.job_queue import close_job_queue

        await close_job_queue()
