# AWS SQS Job Queue Implementation

## Overview

The LoreKeeper job queue system uses AWS SQS (Simple Queue Service) to manage asynchronous asset generation tasks. This allows the API to:

- Decouple request handling from long-running generation processes
- Scale workers independently from the API
- Handle job retries and failure scenarios
- Track job status and history

## Architecture

```
┌─────────────────┐
│   API Server    │
│  (FastAPI)      │
└────────┬────────┘
         │ creates job
         ▼
┌─────────────────┐
│  Database       │
│  (PostgreSQL)   │
│  AssetJob table │
└────────┬────────┘
         │ publish job
         ▼
┌─────────────────┐
│   AWS SQS       │
│ (Job Queue)     │
└────────┬────────┘
         │ poll messages
         ▼
┌─────────────────┐
│   Workers       │
│  (Standalone)   │
│  Process assets │
└────────┬────────┘
         │ update status
         ▼
┌─────────────────┐
│  Database       │
│  Job completed  │
└─────────────────┘
```

## Components

### 1. Job Queue Service (`app/services/job_queue.py`)

The core SQS integration:

- **SQSJobQueue**: Main queue client
  - `initialize()`: Initialize queue connection
  - `enqueue_asset_job()`: Publish job to queue
  - `receive_messages()`: Poll queue for jobs
  - `delete_message()`: Remove processed message
  - `change_message_visibility()`: Retry mechanism
  - `get_queue_attributes()`: Monitor queue status

**Example:**
```python
from app.services.job_queue import get_job_queue

queue = await get_job_queue()
message_id = await queue.enqueue_asset_job(
    job_id="12345",
    payload=asset_generation_payload,
    priority=5
)
```

### 2. Job Producer (`app/services/job_producer.py`)

Publishes jobs from the API:

- **JobProducer.publish_asset_job()**: Publish a job to the queue
- **JobProducer.publish_asset_job_by_id()**: Publish by database ID

**Integration Point:**
The `create_job_and_derivation()` function in `app/services/asset_job_service.py` automatically publishes jobs when `publish_to_queue=True`.

```python
# Automatic on job creation
response = await create_job_and_derivation(
    ...,
    publish_to_queue=True,  # Publishes to SQS
)
```

### 3. Job Consumer (`app/services/job_consumer.py`)

Processes jobs on worker nodes:

- **JobConsumer**: Message polling and processing
  - `register_handler()`: Register job type handler
  - `process_message()`: Process single message
  - `run()`: Blocking event loop
  - `stop()`: Graceful shutdown

**Key Features:**
- Long polling (configurable wait time)
- Automatic message deletion on success
- Visibility timeout extension on failure (retry)
- Structured logging

### 4. Example Worker (`app/workers/asset_generation_worker.py`)

Example implementation:

- **AssetGenerationWorker**: Handles asset generation jobs
- **create_and_run_worker()**: Startup function

## Configuration

Add to `.env`:

```env
# AWS SQS Settings
SQS_QUEUE_NAME=lorekeeper-jobs
SQS_REGION=us-east-1

# AWS Credentials (loaded from environment or ~/.aws/credentials)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

## Usage

### Creating an Asset Job (API Side)

Jobs are automatically published when created via the API:

```python
# POST /assets/asset-jobs
{
  "world_id": "123e4567-e89b-12d3-a456-426614174000",
  "asset_type": "VIDEO",
  "provider": "sora",
  "model_id": "sora-1.0",
  "prompt_spec": {
    "description": "A dragon flying over mountains"
  }
}

# Response includes job_id and status=QUEUED
```

The job is automatically:
1. Stored in PostgreSQL
2. Published to SQS
3. Assigned status: QUEUED

### Processing Jobs (Worker Side)

Run the worker process:

```python
# main_worker.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.workers.asset_generation_worker import create_and_run_worker

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    await create_and_run_worker(async_session_maker)

if __name__ == "__main__":
    asyncio.run(main())
```

Run worker:
```bash
python main_worker.py
```

### Job Lifecycle

1. **QUEUED** (API creates job)
   - Job record created in database
   - Published to SQS queue
   - Waits for worker pickup

2. **PROCESSING** (Worker picks up job)
   - Worker receives message
   - Updates job status to PROCESSING
   - Starts asset generation

3. **SUCCEEDED** (Generation completes)
   - Creates Asset record
   - Updates job status to SUCCEEDED
   - Message deleted from queue

4. **FAILED** (Generation errors)
   - Updates job status to FAILED
   - Stores error_code and error_message
   - Message visibility extended (retry later)

## Error Handling & Retries

### Automatic Retries

Messages that fail processing have their visibility timeout extended:

```python
# On error:
await queue.change_message_visibility(
    receipt_handle=receipt_handle,
    visibility_timeout=60  # Retry in 60 seconds
)
```

The message becomes visible again after the timeout and can be retried.

### Maximum Retries

Configure in queue attributes:
```python
# In SQSJobQueue.__init__()
"MessageRetentionPeriod": "1209600",  # 14 days to retry
```

### Dead Letter Queue (Optional)

For production, configure SQS Dead Letter Queue:

1. Create a separate queue for failed messages
2. Set up redrive policy in main queue
3. Monitor DLQ for stuck jobs

## Monitoring & Status

### Check Queue Status

```python
queue = await get_job_queue()
attrs = await queue.get_queue_attributes()
print(f"Messages available: {attrs['ApproximateNumberOfMessages']}")
print(f"Messages in-flight: {attrs['ApproximateNumberOfMessagesNotVisible']}")
```

### Monitor Job Status

Check via API:
```bash
GET /assets/asset-jobs/{job_id}
```

Returns job status, timestamps, and error details if failed.

## Performance Tuning

### Queue Attributes

```python
Attributes={
    "VisibilityTimeout": "900",      # 15 min to process
    "MessageRetentionPeriod": "1209600",  # 14 days
    "ReceiveMessageWaitTimeSeconds": "20",  # Long polling
}
```

### Consumer Polling

```python
await consumer.run(
    max_messages=1,           # 1-10 messages per poll
    wait_time_seconds=20,     # Long polling timeout
    poll_interval=1.0,        # Delay between polls
)
```

Adjust based on:
- Job volume and throughput
- Processing time per job
- CPU/memory constraints

## Cost Optimization

AWS SQS pricing:
- Free tier: 1M requests/month
- Standard: $0.40 per million requests
- FIFO: $0.50 per million requests

Tips:
- Use batch operations when possible
- Increase VisibilityTimeout to match processing time
- Use long polling (included, saves costs)
- Monitor DLQ to prevent wasted retries

## Development & Testing

### Local Testing with LocalStack

```bash
# Install localstack
pip install localstack

# Start local SQS
localstack start

# Configure for local SQS
SQS_QUEUE_NAME=lorekeeper-jobs
SQS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:4566  # LocalStack endpoint
```

### Purge Queue (Development Only)

```python
queue = await get_job_queue()
await queue.purge_queue()  # Warning: Deletes all messages!
```

## Troubleshooting

### Messages Not Processing

1. Check worker is running: `ps aux | grep worker`
2. Check queue has messages: `get_queue_attributes()`
3. Check worker logs for errors
4. Verify AWS credentials configured
5. Check SQS queue permissions

### Jobs Stuck in Processing

1. Increase VisibilityTimeout if jobs need more time
2. Check for worker crashes: Check application logs
3. Monitor CloudWatch for queue metrics
4. Consider DLQ redrive if repeatedly failing

### High Latency

1. Increase max_messages in consumer.run()
2. Reduce wait_time_seconds for faster polling
3. Scale workers horizontally
4. Monitor database performance (job status updates)

## Future Enhancements

- [ ] FIFO queue support for strict ordering
- [ ] Priority queue using multiple queues
- [ ] Async job callback webhooks
- [ ] CloudWatch metrics integration
- [ ] Job scheduling (delayed execution)
- [ ] Batch processing optimization
