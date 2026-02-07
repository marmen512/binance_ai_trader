# Job Management Quick Start

## Problem Solved
When jobs fail in the Redis Queue (RQ) system, there was no easy way to retry them. This implementation adds a complete job management API.

## Quick Start

### 1. Start the API Server
```bash
uvicorn app.main:app --reload
```

### 2. Check Failed Jobs
```bash
curl http://localhost:8000/api/v1/jobs/failed
```

### 3. Retry All Failed Jobs
```bash
curl -X POST http://localhost:8000/api/v1/jobs/failed/retry-all
```

### 4. Monitor Queue Stats
```bash
curl http://localhost:8000/api/v1/jobs/stats
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/jobs/failed` | List all failed jobs |
| POST | `/api/v1/jobs/failed/{job_id}/retry` | Retry a specific job |
| POST | `/api/v1/jobs/failed/retry-all` | Retry all failed jobs |
| DELETE | `/api/v1/jobs/failed/{job_id}` | Delete a specific job |
| DELETE | `/api/v1/jobs/failed/clear` | Clear all failed jobs |
| GET | `/api/v1/jobs/status/{job_id}` | Get job status |
| GET | `/api/v1/jobs/stats` | Get queue statistics |

## Key Features

✅ **List Failed Jobs** - See all jobs that have failed with error details
✅ **Retry Jobs** - Retry individual jobs or all at once
✅ **Delete Jobs** - Clean up jobs that shouldn't be retried
✅ **Monitor Queue** - Real-time statistics about job queue
✅ **Idempotent** - Safe to retry jobs multiple times
✅ **Error Logging** - Comprehensive logging for debugging

## Architecture

```
┌─────────────┐
│   FastAPI   │
│    API      │
└──────┬──────┘
       │
       ├─────► /api/v1/jobs/failed ────────┐
       │                                    │
       ├─────► /api/v1/jobs/failed/retry ──┤
       │                                    │
       └─────► /api/v1/jobs/stats ─────────┤
                                            │
                                            ▼
                                   ┌────────────────┐
                                   │  Redis Queue   │
                                   │  (RQ System)   │
                                   └────────────────┘
                                            │
                                            ▼
                                   ┌────────────────┐
                                   │  RQ Workers    │
                                   │  Process Jobs  │
                                   └────────────────┘
```

## Python Usage Example

```python
import requests

base_url = "http://localhost:8000/api/v1/jobs"

# Get queue stats
response = requests.get(f"{base_url}/stats")
stats = response.json()
print(f"Failed jobs: {stats['failed_count']}")

# List failed jobs
response = requests.get(f"{base_url}/failed")
failed_jobs = response.json()

for job in failed_jobs:
    print(f"Job {job['job_id']}: {job['func_name']}")
    print(f"  Error: {job['exc_info']}")

# Retry all failed jobs
if stats['failed_count'] > 0:
    response = requests.post(f"{base_url}/failed/retry-all")
    result = response.json()
    print(f"✓ Requeued {result['requeued_count']} jobs")
```

## Testing

Run the test suite:
```bash
pytest app/tests/test_jobs_api.py -v
```

## Documentation

For complete documentation, see [docs/JOB_MANAGEMENT_API.md](JOB_MANAGEMENT_API.md)

## Implementation Details

### Idempotent Jobs
All job functions check if they've already been processed before executing:
```python
# Skip if already processed
if rep.status == "closed":
    return {"success": True, "status": "already_closed"}
```

### Error Handling
Jobs have proper try-catch blocks and logging:
```python
try:
    # Process job
    process_data()
except Exception as e:
    logger.error(f"Job failed: {str(e)}", exc_info=True)
    raise  # Re-raise to mark as failed
```

### Safe Retries
Failed jobs can be retried using RQ's requeue mechanism:
```python
registry = FailedJobRegistry(queue=q)
registry.requeue(job_id)
```

## Troubleshooting

**Q: Jobs keep failing after retry?**
A: Check the error logs and ensure the root cause is fixed before retrying.

**Q: How do I prevent a job from being retried?**
A: Use the DELETE endpoint to remove it from the failed jobs registry.

**Q: Can I retry jobs automatically?**
A: Yes, you can set up a cron job to call the retry-all endpoint periodically.

## Next Steps

1. Monitor the queue statistics regularly
2. Set up alerts for high failure rates
3. Review failed job errors before retrying
4. Consider implementing automatic retry policies
5. Add monitoring dashboards for queue health
