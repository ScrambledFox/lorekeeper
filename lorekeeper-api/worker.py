#!/usr/bin/env python3
"""
LoreKeeper Asset Generation Worker

Standalone worker process for processing asset generation jobs from the SQS queue.

Usage:
    python worker.py                    # Start worker
    python worker.py --help             # Show help
    python worker.py --queue-name=my-queue  # Custom queue name
"""

import argparse
import asyncio
import logging
import signal
import sys
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.db.assets import AssetJobStatus
from app.repositories.assets import AssetRepository
from app.services.job_consumer import JobConsumer, get_job_consumer
from app.services.job_queue import close_job_queue, get_job_queue
from app.types.job_queue import AssetGenerationPayload, JobType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AssetGenerationWorker:
    """Worker for processing asset generation jobs."""

    def __init__(
        self,
        consumer: JobConsumer,
        async_session_maker: sessionmaker,
    ):
        """Initialize worker.

        Args:
            consumer: Job consumer instance
            async_session_maker: SQLAlchemy async session factory
        """
        self.consumer = consumer
        self.async_session_maker = async_session_maker
        self.asset_repo = AssetRepository()
        self.should_exit = False

    async def handle_asset_generation(self, payload: AssetGenerationPayload) -> None:
        """Handle an asset generation job.

        Args:
            payload: Asset generation payload
        """
        async with self.async_session_maker() as session:
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

                # TODO: Call actual generation provider based on payload.provider
                # For now, simulate processing
                logger.info(
                    f"Simulating asset generation: {payload.asset_type} via {payload.provider}"
                )
                await asyncio.sleep(2)  # Simulate work

                # Update job status to SUCCEEDED
                await self.asset_repo.update_asset_job_status(
                    session=session,
                    asset_job_id=payload.asset_job_id,
                    status=AssetJobStatus.SUCCEEDED,
                    finished_at=datetime.utcnow(),
                )
                await session.commit()

                logger.info(f"✓ Successfully completed asset job {payload.asset_job_id}")

            except Exception as e:
                logger.error(
                    f"✗ Error processing asset job {payload.asset_job_id}: {e}",
                    exc_info=True,
                )

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

    async def run(self) -> None:
        """Run the worker (blocking event loop)."""

        # Register handler
        async def handle_job(payload: AssetGenerationPayload) -> None:
            await self.handle_asset_generation(payload)

        self.consumer.register_handler(JobType.ASSET_GENERATION, handle_job)

        # Run consumer
        try:
            await self.consumer.run(
                max_messages=1,
                wait_time_seconds=20,
                poll_interval=1.0,
            )
        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
            self.should_exit = True

    def handle_signal(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.should_exit = True
        self.consumer.stop()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LoreKeeper Asset Generation Worker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python worker.py                           # Start with default settings
  python worker.py --queue-name custom-queue    # Use custom queue
  python worker.py --max-messages 5          # Receive 5 messages per poll
        """,
    )
    parser.add_argument(
        "--queue-name",
        default=settings.SQS_QUEUE_NAME,
        help=f"SQS queue name (default: {settings.SQS_QUEUE_NAME})",
    )
    parser.add_argument(
        "--region",
        default=settings.SQS_REGION,
        help=f"AWS region (default: {settings.SQS_REGION})",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=1,
        help="Max messages to receive per poll (1-10, default: 1)",
    )
    parser.add_argument(
        "--wait-time",
        type=int,
        default=20,
        help="Long polling wait time in seconds (0-20, default: 20)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Interval between polls in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("LoreKeeper Asset Generation Worker")
    logger.info("=" * 60)
    logger.info(f"Queue Name: {args.queue_name}")
    logger.info(f"Region: {args.region}")
    logger.info(f"Max Messages: {args.max_messages}")
    logger.info(f"Wait Time: {args.wait_time}s")
    logger.info(f"Poll Interval: {args.poll_interval}s")
    logger.info("=" * 60)

    # Create database session factory
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=args.debug,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
    )
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create consumer and worker
    consumer = await get_job_consumer(async_session_maker)
    worker = AssetGenerationWorker(consumer, async_session_maker)

    # Register signal handlers for graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, worker.handle_signal)

    try:
        logger.info("Starting worker...")
        await worker.run()
    finally:
        logger.info("Cleaning up...")
        await close_job_queue()
        await engine.dispose()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
