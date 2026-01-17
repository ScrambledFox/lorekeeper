"""Tests for job queue functionality."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from app.services.job_queue import SQSJobQueue
from app.services.job_producer import JobProducer
from app.services.job_consumer import JobConsumer
from app.types.job_queue import (
    AssetGenerationPayload,
    JobType,
    QueuedMessage,
    ReceivedMessage,
)


class TestSQSJobQueue:
    """Tests for SQSJobQueue."""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test queue initialization."""
        with patch("boto3.client") as mock_client:
            mock_sqs = MagicMock()
            mock_client.return_value = mock_sqs
            mock_sqs.get_queue_url.return_value = {
                "QueueUrl": "https://sqs.us-east-1.amazonaws.com/123/test"
            }

            queue = SQSJobQueue("test-queue", "us-east-1")
            await queue.initialize()

            assert queue._initialized
            assert queue.queue_url == "https://sqs.us-east-1.amazonaws.com/123/test"

    @pytest.mark.asyncio
    async def test_enqueue_asset_job(self):
        """Test enqueueing an asset job."""
        with patch("boto3.client") as mock_client:
            mock_sqs = MagicMock()
            mock_client.return_value = mock_sqs
            mock_sqs.get_queue_url.return_value = {"QueueUrl": "https://test-queue"}
            mock_sqs.send_message.return_value = {"MessageId": "msg-123"}

            queue = SQSJobQueue("test-queue")
            await queue.initialize()

            payload = AssetGenerationPayload(
                asset_job_id=uuid4(),
                world_id=uuid4(),
                asset_type="VIDEO",
                provider="sora",
                model_id="sora-1.0",
                prompt_spec={"description": "test"},
                requested_by="user-1",
            )

            message_id = await queue.enqueue_asset_job(
                job_id="job-123",
                payload=payload,
                priority=5,
            )

            assert message_id == "msg-123"
            mock_sqs.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_receive_messages(self):
        """Test receiving messages from queue."""
        with patch("boto3.client") as mock_client:
            mock_sqs = MagicMock()
            mock_client.return_value = mock_sqs
            mock_sqs.get_queue_url.return_value = {"QueueUrl": "https://test-queue"}
            mock_sqs.receive_message.return_value = {
                "Messages": [
                    {
                        "MessageId": "msg-1",
                        "Body": '{"job_type": "ASSET_GENERATION"}',
                        "ReceiptHandle": "receipt-1",
                    }
                ]
            }

            queue = SQSJobQueue("test-queue")
            await queue.initialize()

            messages = await queue.receive_messages(max_messages=1)

            assert len(messages) == 1
            assert messages[0].message_id == "msg-1"
            assert messages[0].receipt_handle == "receipt-1"

    @pytest.mark.asyncio
    async def test_delete_message(self):
        """Test deleting a message."""
        with patch("boto3.client") as mock_client:
            mock_sqs = MagicMock()
            mock_client.return_value = mock_sqs
            mock_sqs.get_queue_url.return_value = {"QueueUrl": "https://test-queue"}

            queue = SQSJobQueue("test-queue")
            await queue.initialize()

            await queue.delete_message("receipt-handle-123")

            mock_sqs.delete_message.assert_called_once()


class TestJobProducer:
    """Tests for JobProducer."""

    @pytest.mark.asyncio
    async def test_publish_asset_job(self):
        """Test publishing an asset job."""
        mock_queue = AsyncMock()
        mock_queue.enqueue_asset_job = AsyncMock(return_value="msg-123")

        producer = JobProducer(mock_queue)

        # Create mock asset job
        mock_job = MagicMock()
        mock_job.id = uuid4()
        mock_job.world_id = uuid4()
        mock_job.asset_type = "VIDEO"
        mock_job.provider = "sora"
        mock_job.model_id = "sora-1.0"
        mock_job.prompt_spec = {"description": "test"}
        mock_job.priority = 5
        mock_job.requested_by = "user-1"

        mock_repo = AsyncMock()
        mock_session = MagicMock()

        message_id = await producer.publish_asset_job(
            asset_repo=mock_repo,
            session=mock_session,
            asset_job=mock_job,
        )

        assert message_id == "msg-123"
        mock_queue.enqueue_asset_job.assert_called_once()


class TestJobConsumer:
    """Tests for JobConsumer."""

    @pytest.mark.asyncio
    async def test_register_handler(self):
        """Test registering a job handler."""
        mock_queue = MagicMock()
        mock_session_maker = MagicMock()

        consumer = JobConsumer(mock_queue, mock_session_maker)

        async def handler(payload):
            pass

        consumer.register_handler(JobType.ASSET_GENERATION, handler)

        assert JobType.ASSET_GENERATION in consumer.handlers

    @pytest.mark.asyncio
    async def test_process_message_success(self):
        """Test successfully processing a message."""
        mock_queue = MagicMock()
        mock_session_maker = MagicMock()

        consumer = JobConsumer(mock_queue, mock_session_maker)

        # Create test message
        payload = AssetGenerationPayload(
            asset_job_id=uuid4(),
            world_id=uuid4(),
            asset_type="VIDEO",
            provider="sora",
            model_id="sora-1.0",
            prompt_spec={"description": "test"},
            requested_by="user-1",
        )

        message_body = QueuedMessage(
            job_type=JobType.ASSET_GENERATION,
            payload=payload.model_dump(by_alias=True),
        ).model_dump_json()

        message = ReceivedMessage(
            message_id="msg-1",
            body=message_body,
            receipt_handle="receipt-1",
        )

        # Register handler
        handler_called = False

        async def handler(p):
            nonlocal handler_called
            handler_called = True

        consumer.register_handler(JobType.ASSET_GENERATION, handler)
        mock_queue.delete_message = AsyncMock()

        success = await consumer.process_message(message)

        assert success
        assert handler_called
        mock_queue.delete_message.assert_called_once_with("receipt-1")

    @pytest.mark.asyncio
    async def test_process_message_invalid_format(self):
        """Test processing invalid message format."""
        mock_queue = MagicMock()
        mock_session_maker = MagicMock()

        consumer = JobConsumer(mock_queue, mock_session_maker)

        message = ReceivedMessage(
            message_id="msg-1",
            body="invalid json",
            receipt_handle="receipt-1",
        )

        success = await consumer.process_message(message)

        assert not success
        mock_queue.delete_message.assert_not_called()
