# Quick Start Guide - AWS SQS Job Queue

## 5-Minute Setup

### Prerequisites
- AWS Account with SQS access
- Python 3.11+
- PostgreSQL database
- LoreKeeper API running

### Step 1: Configure Environment

Update `.env`:
```env
# Add these lines
SQS_QUEUE_NAME=lorekeeper-jobs
SQS_REGION=us-east-1

# AWS credentials (use ~/.aws/credentials or set these)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Step 2: Create SQS Queue

Via AWS Console:
1. Go to SQS dashboard
2. Click "Create queue"
3. Enter name: `lorekeeper-jobs`
4. Select "Standard" queue type
5. Leave other settings as default
6. Click "Create queue"

**Or via AWS CLI:**
```bash
aws sqs create-queue \
  --queue-name lorekeeper-jobs \
  --region us-east-1
```

### Step 3: Install Dependencies

Dependencies already included in `pyproject.toml`:
- `boto3>=1.26.0` - AWS SDK
- `asyncpg>=0.29.0` - Database
- `sqlalchemy>=2.0.25` - ORM

No additional dependencies needed!

### Step 4: Start API Server

```bash
uvicorn app.main:app --reload
```

### Step 5: Start Worker

In a new terminal:
```bash
python worker.py
```

Expected output:
```
============================================================
LoreKeeper Asset Generation Worker
============================================================
Queue Name: lorekeeper-jobs
Region: us-east-1
Max Messages: 1
Wait Time: 20s
Poll Interval: 1.0s
============================================================
Starting worker...
```

### Step 6: Test It

Create an asset job:
```bash
curl -X POST http://localhost:8000/assets/asset-jobs \
  -H "Content-Type: application/json" \
  -H "user-id: test-user" \
  -d '{
    "world_id": "123e4567-e89b-12d3-a456-426614174000",
    "asset_type": "VIDEO",
    "provider": "sora",
    "model_id": "sora-1.0",
    "prompt_spec": {
      "description": "A dragon flying"
    }
  }'
```

Watch worker output:
```
Processing asset job <job-id>: type=VIDEO, provider=sora
Simulating asset generation: VIDEO via sora
✓ Successfully completed asset job <job-id>
```

## File Structure

```
app/
├── services/
│   ├── job_queue.py           # Core SQS integration
│   ├── job_producer.py        # Publish jobs
│   └── job_consumer.py        # Process jobs
├── workers/
│   └── asset_generation_worker.py  # Example handler
├── types/
│   └── job_queue.py           # Type definitions
└── core/
    └── config.py              # SQS settings

worker.py                        # Standalone worker script
docs/JOB_QUEUE.md              # Full documentation
tests/test_job_queue.py        # Unit tests
```

## Common Commands

### Check Queue Status
```python
from app.services.job_queue import get_job_queue

queue = await get_job_queue()
attrs = await queue.get_queue_attributes()
print(f"Messages: {attrs['ApproximateNumberOfMessages']}")
```

### Check Job Status
```bash
curl http://localhost:8000/assets/asset-jobs/{job-id}
```

### Start Worker with Custom Settings
```bash
python worker.py --max-messages 5 --wait-time 20 --debug
```

### View Worker Help
```bash
python worker.py --help
```

### Purge Queue (Development Only)
```python
queue = await get_job_queue()
await queue.purge_queue()  # Deletes all messages!
```

## Local Testing with LocalStack

For development without AWS account:

```bash
# Install localstack
pip install localstack

# Start localstack
localstack start

# In .env, add:
AWS_ENDPOINT_URL=http://localhost:4566

# Run normally
python worker.py
```

## Troubleshooting

**"Queue does not exist"**
- Verify queue exists in AWS SQS console
- Check queue name matches `SQS_QUEUE_NAME` in .env
- Verify AWS credentials have SQS permissions

**"No module named 'boto3'"**
```bash
uv sync  # Reinstall dependencies
```

**"Worker not processing jobs"**
1. Check worker is running: `ps aux | grep worker.py`
2. Check API logs for publishing errors
3. Verify SQS queue URL is correct
4. Check AWS credentials are set

**"Jobs stuck in PROCESSING"**
- Increase visibility timeout in queue settings (default: 900s)
- Check worker logs for exceptions
- Manually update job status if needed

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  API Server (FastAPI)                                │
│  - Create asset job                                  │
│  - Automatically publish to SQS                      │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
        ┌────────────────┐
        │   PostgreSQL   │
        │  Asset Jobs    │
        └────────┬───────┘
                 │
                 ▼
        ┌────────────────┐
        │   AWS SQS      │
        │  lorekeeper    │
        │   -jobs        │
        └────────┬───────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│  Worker Process                                      │
│  - Poll SQS queue                                    │
│  - Process asset jobs                               │
│  - Update database status                           │
└──────────────────────────────────────────────────────┘
```

## Example Worker Implementation

The provided `app/workers/asset_generation_worker.py` shows:
1. How to handle job payloads
2. How to update job status
3. How to track errors
4. How to integrate with database

Customize it to call actual generation providers:

```python
async def handle_asset_generation(self, payload: AssetGenerationPayload):
    # ... (setup code)
    
    # Call your provider
    if payload.provider == "sora":
        result = await sora_api.generate_video(payload.prompt_spec)
    elif payload.provider == "my_provider":
        result = await my_provider.generate(payload)
    
    # Store result
    await store_asset_to_s3(result)
    
    # ... (success/error handling)
```

## Next Steps

1. **Create AWS SQS Queue** - Follow "Step 2" above
2. **Configure Environment** - Update `.env` with credentials
3. **Test Locally** - Use LocalStack or real AWS
4. **Deploy Workers** - Run on dedicated machines/containers
5. **Monitor Jobs** - Set up CloudWatch alarms
6. **Integrate Providers** - Update worker to call real APIs

## Performance Tips

- **Increase Workers**: Run multiple worker processes for higher throughput
- **Tune Poll Interval**: Reduce for lower latency, increase to save CPU
- **Batch Processing**: Increase `max_messages` for bulk jobs
- **Database**: Ensure PostgreSQL can handle concurrent updates

## Need Help?

- Check `docs/JOB_QUEUE.md` for full documentation
- Review `tests/test_job_queue.py` for usage examples
- Check worker logs for detailed error messages
- Review AWS SQS documentation for queue tuning

Happy queueing! 🚀
