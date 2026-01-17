"""Job consumer service for processing asset generation tasks from the queue."""

import asyncio
import json
import logging
from typing import Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.db.assets import AssetJobStatus
from app.repositories.assets import AssetRepository
from app.services.job_queue import SQSJobQueue, get_job_queue
from app.types.job_queue import (
    AssetGenerationPayload,
    JobType,
    QueueOperationError,
    ReceivedMessage,
)

logger = logging.getLogger(__name__)


class JobConsumer:
    """Service for consuming (processing) jobs from the queue."""

    def __init__(
        self,
        queue: SQSJobQueue,
        async_session_maker: sessionmaker,
        asset_repo_class: type = AssetRepository,
    ):
        """Initialize the job consumer.

        Args:
            queue: SQS job queue instance
            async_session_maker: SQLAlchemy async session factory
            asset_repo_class: Asset repository class (for dependency injection)
        """
        self.queue = queue
        self.async_session_maker = async_session_maker
        self.AssetRepository = asset_repo_class
        self.is_running = False
        self.handlers: dict[JobType, Callable] = {}

    def register_handler(self, job_type: JobType, handler: Callable) -> None:
        """Register a handler for a specific job type.

        Args:
            job_type: Type of job to handle
            handler: Async function that processes the job
        """
        self.handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type}")

    async def process_message(self, message: ReceivedMessage) -> bool:
        """Process a single message from the queue.

        Args:
            message: Message received from queue

        Returns:
            True if processed successfully, False otherwise

        Raises:
            Exception: If processing fails (will be caught and logged)
        """
        try:
            # Parse the message body
            body = json.loads(message.body)
            job_type = JobType(body.get("job_type"))
            payload_data = body.get("payload", {})

            logger.info(
                f"Processing message {message.message_id}: job_type={job_type}, "
                f"asset_job_id={payload_data.get('asset_job_id')}"
            )

            # Get the handler
            handler = self.handlers.get(job_type)
            if not handler:
                logger.error(f"No handler registered for job type: {job_type}")
                return False

            # Parse payload based on job type
            if job_type == JobType.ASSET_GENERATION:
                payload = AssetGenerationPayload(**payload_data)
                await handler(payload)
            else:
                logger.error(f"Unknown job type: {job_type}")
                return False

            # Delete the message after successful processing
            if message.receipt_handle:
                await self.queue.delete_message(message.receipt_handle)
                logger.info(f"Deleted message {message.message_id} from queue")

            return True

        except ValueError as e:
            logger.error(f"Invalid message format: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing message {message.message_id}: {e}", exc_info=True)
            return False

    async def update_job_status(
        self,
        asset_repo: AssetRepository,
        session: AsyncSession,
        asset_job_id: str,
        status: str,
        started_at=None,
        finished_at=None,
        error_code=None,
        error_message=None,
    ) -> None:
        """Update the status of an asset job in the database.

        Args:
            asset_repo: Asset repository
            session: Database session
            asset_job_id: ID of the asset job
            status: New status
            started_at: When the job started (optional)
            finished_at: When the job finished (optional)
            error_code: Error code if job failed (optional)
            error_message: Error message if job failed (optional)
        """
        from uuid import UUID

        await asset_repo.update_asset_job_status(
            session=session,
            asset_job_id=UUID(asset_job_id),
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            error_code=error_code,
            error_message=error_message,
        )
        await session.commit()

    async def run(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 20,
        poll_interval: float = 1.0,
    ) -> None:
        """Run the job consumer (blocking, infinite loop).

        This method polls the queue continuously and processes messages.

        Args:
            max_messages: Maximum messages to receive per poll
            wait_time_seconds: SQS long polling wait time
            poll_interval: Delay between polls (for graceful shutdown)

        Raises:
            KeyboardInterrupt: When Ctrl+C is pressed
        """
        if not self.handlers:
            logger.error("No handlers registered! Cannot start consumer.")
            return

        self.is_running = True
        logger.info(f"Starting job consumer with {len(self.handlers)} handler(s)")

        try:
            while self.is_running:
                try:
                    # Receive messages from queue
                    messages = await self.queue.receive_messages(
                        max_messages=max_messages,
                        wait_time_seconds=wait_time_seconds,
                    )

                    if not messages:
                        # No messages available, continue polling
                        await asyncio.sleep(poll_interval)
                        continue

                    # Process each message
                    for message in messages:
                        if not self.is_running:
                            break

                        success = await self.process_message(message)
                        if not success and message.receipt_handle:
                            # On failure, increase visibility timeout to retry later
                            try:
                                await self.queue.change_message_visibility(
                                    receipt_handle=message.receipt_handle,
                                    visibility_timeout=60,  # Retry in 60 seconds
                                )
                            except QueueOperationError as e:
                                logger.error(f"Failed to update message visibility: {e}")

                except asyncio.CancelledError:
                    logger.info("Consumer cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in consumer loop: {e}", exc_info=True)
                    await asyncio.sleep(5)  # Back off on error

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down consumer")
        finally:
            self.is_running = False
            logger.info("Job consumer stopped")

    def stop(self) -> None:
        """Stop the consumer gracefully."""
        self.is_running = False
        logger.info("Stopping job consumer")


async def get_job_consumer(
    async_session_maker: Optional[sessionmaker] = None,
) -> JobConsumer:
    """Get a job consumer instance.

    Args:
        async_session_maker: SQLAlchemy async session factory (uses default if not provided)

    Returns:
        JobConsumer instance with initialized queue

    Raises:
        Exception: If queue initialization fails
    """
    queue = await get_job_queue()

    if async_session_maker is None:
        # Create default session maker
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
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

    return JobConsumer(queue, async_session_maker)
