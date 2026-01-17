"""AWS SQS-based job queue implementation."""

import json
import logging
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.types.job_queue import (
    AssetGenerationPayload,
    JobQueueError,
    JobType,
    MessageNotFoundError,
    QueuedMessage,
    QueueOperationError,
    ReceivedMessage,
)

logger = logging.getLogger(__name__)


class SQSJobQueue:
    """AWS SQS-based job queue for distributing asset generation tasks."""

    def __init__(self, queue_name: str = "lorekeeper-jobs", region: str = "us-east-1"):
        """Initialize the SQS job queue.

        Args:
            queue_name: Name of the SQS queue
            region: AWS region for SQS

        Raises:
            QueueOperationError: If queue initialization fails
        """
        self.queue_name = queue_name
        self.region = region
        self.client = boto3.client("sqs", region_name=region)
        self.queue_url: str | None = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize queue and get queue URL.

        Raises:
            QueueOperationError: If initialization fails
        """
        if self._initialized:
            return

        try:
            response = self.client.get_queue_url(QueueName=self.queue_name)
            self.queue_url = response["QueueUrl"]
            logger.info(f"Initialized SQS queue: {self.queue_name} ({self.queue_url})")
            self._initialized = True
        except ClientError as e:
            if e.response["Error"]["Code"] == "QueueDoesNotExist":
                logger.info(f"Queue does not exist, creating: {self.queue_name}")
                await self._create_queue()
            else:
                raise QueueOperationError(
                    f"Failed to get queue URL for {self.queue_name}: {str(e)}"
                )
        except BotoCoreError as e:
            raise QueueOperationError(f"AWS error initializing queue: {str(e)}")

    async def _create_queue(self) -> None:
        """Create the SQS queue if it doesn't exist.

        Raises:
            QueueOperationError: If queue creation fails
        """
        try:
            response = self.client.create_queue(
                QueueName=self.queue_name,
                Attributes={
                    "VisibilityTimeout": "900",  # 15 minutes
                    "MessageRetentionPeriod": "1209600",  # 14 days
                    "ReceiveMessageWaitTimeSeconds": "20",  # Long polling
                },
            )
            self.queue_url = response["QueueUrl"]
            logger.info(f"Created SQS queue: {self.queue_name}")
            self._initialized = True
        except ClientError as e:
            raise QueueOperationError(f"Failed to create queue {self.queue_name}: {str(e)}")

    async def enqueue_asset_job(
        self,
        job_id: str,
        payload: AssetGenerationPayload,
        priority: int | None = None,
        delay_seconds: int = 0,
    ) -> str:
        """Enqueue an asset generation job.

        Args:
            job_id: Unique job identifier
            payload: Asset generation payload
            priority: Job priority (0-9, where 9 is highest)
            delay_seconds: Delay before message becomes visible (0-900)

        Returns:
            Message ID from SQS

        Raises:
            QueueOperationError: If enqueue operation fails
        """
        if not self._initialized:
            await self.initialize()

        try:
            message = QueuedMessage(
                job_type=JobType.ASSET_GENERATION,
                payload=payload.model_dump(by_alias=True),
            )

            response = self.client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=message.model_dump_json(),
                DelaySeconds=delay_seconds,
                MessageAttributes={
                    "job_type": {
                        "StringValue": str(JobType.ASSET_GENERATION),
                        "DataType": "String",
                    },
                    "job_id": {
                        "StringValue": job_id,
                        "DataType": "String",
                    },
                    "priority": {
                        "StringValue": str(priority or 0),
                        "DataType": "Number",
                    },
                    "world_id": {
                        "StringValue": str(payload.world_id),
                        "DataType": "String",
                    },
                },
            )

            message_id = response["MessageId"]
            logger.info(
                f"Enqueued asset job {job_id} with message ID {message_id}, priority={priority}"
            )
            return message_id
        except ClientError as e:
            raise QueueOperationError(f"Failed to enqueue job {job_id}: {str(e)}")

    async def receive_messages(
        self, max_messages: int = 1, wait_time_seconds: int = 20
    ) -> list[ReceivedMessage]:
        """Receive messages from the queue.

        Args:
            max_messages: Maximum number of messages to receive (1-10)
            wait_time_seconds: Long polling wait time (0-20)

        Returns:
            List of received messages

        Raises:
            QueueOperationError: If receive operation fails
        """
        if not self._initialized:
            await self.initialize()

        try:
            response = self.client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=min(wait_time_seconds, 20),
                MessageAttributeNames=["All"],
            )

            messages = []
            for msg in response.get("Messages", []):
                received_msg = ReceivedMessage(
                    message_id=msg["MessageId"],
                    body=msg["Body"],
                    receipt_handle=msg.get("ReceiptHandle"),
                )
                messages.append(received_msg)

            if messages:
                logger.debug(f"Received {len(messages)} messages from queue")

            return messages
        except ClientError as e:
            raise QueueOperationError(f"Failed to receive messages: {str(e)}")

    async def delete_message(self, receipt_handle: str) -> None:
        """Delete a message from the queue.

        Args:
            receipt_handle: Receipt handle from received message

        Raises:
            QueueOperationError: If delete operation fails
        """
        if not self._initialized:
            await self.initialize()

        if not receipt_handle:
            raise MessageNotFoundError("Receipt handle is required")

        try:
            self.client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )
            logger.debug(f"Deleted message from queue: {receipt_handle[:16]}...")
        except ClientError as e:
            raise QueueOperationError(f"Failed to delete message: {str(e)}")

    async def change_message_visibility(self, receipt_handle: str, visibility_timeout: int) -> None:
        """Change the visibility timeout of a message.

        Args:
            receipt_handle: Receipt handle from received message
            visibility_timeout: New visibility timeout in seconds

        Raises:
            QueueOperationError: If operation fails
        """
        if not self._initialized:
            await self.initialize()

        if not receipt_handle:
            raise MessageNotFoundError("Receipt handle is required")

        try:
            self.client.change_message_visibility(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout,
            )
            logger.debug(
                f"Changed message visibility: {receipt_handle[:16]}... -> {visibility_timeout}s"
            )
        except ClientError as e:
            raise QueueOperationError(f"Failed to change message visibility: {str(e)}")

    async def get_queue_attributes(self) -> dict[str, Any]:
        """Get queue attributes.

        Returns:
            Dictionary of queue attributes

        Raises:
            QueueOperationError: If operation fails
        """
        if not self._initialized:
            await self.initialize()

        try:
            response = self.client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=["All"],
            )
            return response.get("Attributes", {})
        except ClientError as e:
            raise QueueOperationError(f"Failed to get queue attributes: {str(e)}")

    async def purge_queue(self) -> None:
        """Purge all messages from the queue (development only).

        Raises:
            QueueOperationError: If operation fails
        """
        if not self._initialized:
            await self.initialize()

        try:
            self.client.purge_queue(QueueUrl=self.queue_url)
            logger.warning(f"Purged all messages from queue: {self.queue_name}")
        except ClientError as e:
            raise QueueOperationError(f"Failed to purge queue: {str(e)}")

    async def close(self) -> None:
        """Close the queue client."""
        if self.client:
            self.client.close()
            logger.info("Closed SQS client")


# Singleton instance
_job_queue: SQSJobQueue | None = None


async def get_job_queue() -> SQSJobQueue:
    """Get or create the job queue singleton.

    Returns:
        SQSJobQueue instance
    """
    global _job_queue
    if _job_queue is None:
        _job_queue = SQSJobQueue(
            queue_name=settings.SQS_QUEUE_NAME,
            region=settings.SQS_REGION,
        )
        await _job_queue.initialize()
    return _job_queue


async def close_job_queue() -> None:
    """Close the job queue."""
    global _job_queue
    if _job_queue:
        await _job_queue.close()
        _job_queue = None
