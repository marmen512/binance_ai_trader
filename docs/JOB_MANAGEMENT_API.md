# Job Management API

## Overview

The Job Management API provides endpoints to monitor, retry, and manage failed jobs in the RQ (Redis Queue) system.

## Endpoints

### 1. List Failed Jobs

Get a list of all failed jobs in the queue.

**Endpoint:** `GET /api/v1/jobs/failed`

**Response:**
```json
[
  {
    "job_id": "abc-123",
    "func_name": "app.workers.jobs.simulate_replicated_trade",
    "args": [1],
    "kwargs": {},
    "created_at": "2024-01-01T12:00:00",
    "ended_at": "2024-01-01T12:01:00",
    "exc_info": "Error message...",
    "result": null
  }
]
```

### 2. Retry a Specific Failed Job

Retry a single failed job by its ID.

**Endpoint:** `POST /api/v1/jobs/failed/{job_id}/retry`

**Response:**
```json
{
  "success": true,
  "job_id": "abc-123",
  "message": "Job abc-123 has been requeued successfully"
}
```

### 3. Retry All Failed Jobs

Retry all failed jobs in the queue.

**Endpoint:** `POST /api/v1/jobs/failed/retry-all`

**Response:**
```json
{
  "success": true,
  "total_failed": 5,
  "requeued_count": 5,
  "error_count": 0,
  "requeued_jobs": ["job-1", "job-2", "job-3", "job-4", "job-5"],
  "errors": []
}
```

### 4. Delete a Failed Job

Remove a specific failed job from the registry.

**Endpoint:** `DELETE /api/v1/jobs/failed/{job_id}`

**Response:**
```json
{
  "success": true,
  "job_id": "abc-123",
  "message": "Job abc-123 has been deleted successfully"
}
```

### 5. Clear All Failed Jobs

Delete all failed jobs from the registry.

**Endpoint:** `DELETE /api/v1/jobs/failed/clear`

**Response:**
```json
{
  "success": true,
  "total_failed": 5,
  "deleted_count": 5,
  "error_count": 0,
  "deleted_jobs": ["job-1", "job-2", "job-3", "job-4", "job-5"],
  "errors": []
}
```

### 6. Get Job Status

Get the current status and details of any job.

**Endpoint:** `GET /api/v1/jobs/status/{job_id}`

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "finished",
  "func_name": "app.workers.jobs.simulate_replicated_trade",
  "args": [1],
  "kwargs": {},
  "created_at": "2024-01-01T12:00:00",
  "started_at": "2024-01-01T12:00:01",
  "ended_at": "2024-01-01T12:01:00",
  "result": "success",
  "exc_info": null,
  "is_finished": true,
  "is_failed": false,
  "is_started": false,
  "is_queued": false
}
```

### 7. Get Queue Statistics

Get overall statistics about the job queue.

**Endpoint:** `GET /api/v1/jobs/stats`

**Response:**
```json
{
  "queue_name": "default",
  "queued_count": 10,
  "failed_count": 2,
  "started_count": 1,
  "finished_count": 50
}
```

## Usage Examples

### Using cURL

```bash
# List all failed jobs
curl http://localhost:8000/api/v1/jobs/failed

# Retry a specific job
curl -X POST http://localhost:8000/api/v1/jobs/failed/abc-123/retry

# Retry all failed jobs
curl -X POST http://localhost:8000/api/v1/jobs/failed/retry-all

# Get queue statistics
curl http://localhost:8000/api/v1/jobs/stats

# Get job status
curl http://localhost:8000/api/v1/jobs/status/abc-123

# Delete a failed job
curl -X DELETE http://localhost:8000/api/v1/jobs/failed/abc-123

# Clear all failed jobs
curl -X DELETE http://localhost:8000/api/v1/jobs/failed/clear
```

### Using Python requests

```python
import requests

base_url = "http://localhost:8000/api/v1/jobs"

# List failed jobs
response = requests.get(f"{base_url}/failed")
failed_jobs = response.json()

# Retry all failed jobs
response = requests.post(f"{base_url}/failed/retry-all")
result = response.json()
print(f"Requeued {result['requeued_count']} jobs")

# Get queue stats
response = requests.get(f"{base_url}/stats")
stats = response.json()
print(f"Failed jobs: {stats['failed_count']}")
```

## Job Retry Behavior

- Jobs are retried by re-enqueueing them to the queue
- The job functions are designed to be **idempotent** (safe to run multiple times)
- Jobs that have already completed will detect this and skip processing
- Error logging is included for debugging failed jobs

## Best Practices

1. **Monitor Failed Jobs Regularly**: Check the `/api/v1/jobs/stats` endpoint periodically
2. **Investigate Before Retrying**: Review the error details in failed jobs before retrying
3. **Retry Selectively**: Consider retrying jobs one at a time if the failure was specific
4. **Clean Up Old Failures**: Use the clear endpoint to remove permanently failed jobs
5. **Check Job Status**: Use the status endpoint to track job progress

## Error Handling

All endpoints return appropriate HTTP status codes:
- `200 OK`: Successful operation
- `404 Not Found`: Job not found
- `500 Internal Server Error`: Server-side error

Error responses include a `detail` field with the error message:
```json
{
  "detail": "Job abc-123 not found in failed jobs registry"
}
```
