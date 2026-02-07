"""
Jobs management API router with safety features.

Provides endpoints to manage RQ jobs including viewing and retrying failed jobs
with idempotency guards, retry policies, and audit logging.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import FailedJobRegistry, StartedJobRegistry, FinishedJobRegistry
from app.core.config import settings
from app.job_safety import (
    RetryGuard, 
    RetryPolicy, 
    RetryLimits,
    FailureClassifier,
    RetryAuditLogger
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
redis_conn = Redis.from_url(settings.REDIS_URL)
q = Queue(connection=redis_conn)

# Initialize job safety components
retry_guard = RetryGuard(redis_conn)
retry_policy = RetryPolicy(redis_conn, RetryLimits(
    max_retries=getattr(settings, 'RETRY_MAX_ATTEMPTS', 3),
    cooldown_seconds=getattr(settings, 'RETRY_COOLDOWN_SECONDS', 60)
))
failure_classifier = FailureClassifier()
audit_logger = RetryAuditLogger()


@router.get("/failed")
def list_failed_jobs() -> List[Dict[str, Any]]:
    """
    List all failed jobs in the queue with retry status.
    
    Returns:
        List of failed jobs with their details, failure classification, and retry status
    """
    registry = FailedJobRegistry(queue=q)
    failed_jobs = []
    
    for job_id in registry.get_job_ids():
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            
            # Classify failure
            failure_type = failure_classifier.classify_failure(job.exc_info or "")
            is_retryable = failure_classifier.is_retryable(failure_type)
            
            # Get retry status
            retry_status = retry_policy.get_retry_status(job)
            
            failed_jobs.append({
                "job_id": job.id,
                "func_name": job.func_name,
                "args": job.args,
                "kwargs": job.kwargs,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "exc_info": job.exc_info,
                "result": str(job.result) if job.result else None,
                "failure_type": failure_type.value,
                "is_retryable": is_retryable,
                "retry_status": retry_status,
            })
        except Exception as e:
            logger.error(f"Error fetching job {job_id}: {str(e)}")
            failed_jobs.append({
                "job_id": job_id,
                "error": f"Failed to fetch job details: {str(e)}"
            })
    
    return failed_jobs


@router.post("/failed/{job_id}/retry")
def retry_failed_job(
    job_id: str,
    dry_run: bool = Query(False, description="Simulate retry without executing"),
    retry_only_retryable: bool = Query(True, description="Only retry if failure is retryable"),
    force: bool = Query(False, description="Force retry ignoring cooldown")
) -> Dict[str, Any]:
    """
    Retry a specific failed job with safety checks.
    
    Args:
        job_id: The ID of the job to retry
        dry_run: If True, simulate without actually retrying
        retry_only_retryable: If True, only retry retryable failures
        force: If True, ignore cooldown period
        
    Returns:
        Status of the retry operation with safety information
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        # Check if job exists and is failed
        registry = FailedJobRegistry(queue=q)
        if job_id not in registry.get_job_ids():
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found in failed jobs registry"
            )
        
        # Classify failure
        exc_info = job.exc_info or ""
        should_retry, failure_type = failure_classifier.should_retry_failure(exc_info)
        
        # Check if retryable
        if retry_only_retryable and not should_retry:
            message = (
                f"Job {job_id} has non-retryable failure type: {failure_type.value}. "
                f"Use force=true to override."
            )
            logger.warning(message)
            
            # Log to audit
            audit_logger.log_retry_attempt(
                job=job,
                retry_reason="blocked_non_retryable",
                failure_type=failure_type.value,
                dry_run=dry_run,
                success=False,
                error_message=message
            )
            
            return {
                "success": False,
                "job_id": job_id,
                "failure_type": failure_type.value,
                "is_retryable": should_retry,
                "message": message
            }
        
        # Check retry policy
        can_retry, reason = retry_policy.can_retry(job)
        
        if not can_retry and not force:
            logger.warning(f"Job {job_id} cannot retry: {reason}")
            
            # Log to audit
            audit_logger.log_retry_attempt(
                job=job,
                retry_reason="blocked_policy",
                failure_type=failure_type.value,
                dry_run=dry_run,
                success=False,
                error_message=reason
            )
            
            return {
                "success": False,
                "job_id": job_id,
                "failure_type": failure_type.value,
                "can_retry": False,
                "reason": reason,
                "message": f"Retry blocked: {reason}. Use force=true to override."
            }
        
        # Dry run - just log and return
        if dry_run:
            logger.info(f"DRY RUN: Would retry job {job_id}")
            
            audit_logger.log_dry_run(
                job=job,
                retry_reason="user_initiated",
                failure_type=failure_type.value,
                user_or_system="user"
            )
            
            return {
                "success": True,
                "job_id": job_id,
                "failure_type": failure_type.value,
                "dry_run": True,
                "message": f"DRY RUN: Job {job_id} would be requeued successfully"
            }
        
        # Record retry attempt
        retry_policy.record_retry_attempt(job)
        
        # Log to audit
        audit_logger.log_retry_attempt(
            job=job,
            retry_reason="user_initiated",
            failure_type=failure_type.value,
            dry_run=False,
            user_or_system="user"
        )
        
        # Requeue the job
        registry.requeue(job_id)
        
        logger.info(f"Successfully requeued job {job_id}")
        
        return {
            "success": True,
            "job_id": job_id,
            "failure_type": failure_type.value,
            "retry_attempt": job.meta.get('retry_attempts', 1),
            "message": f"Job {job_id} has been requeued successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry job {job_id}: {str(e)}"
        )


@router.post("/failed/retry-all")
def retry_all_failed_jobs(
    dry_run: bool = Query(False, description="Simulate retry without executing"),
    retry_only_retryable: bool = Query(True, description="Only retry retryable failures")
) -> Dict[str, Any]:
    """
    Retry all failed jobs in the queue with safety checks.
    
    Args:
        dry_run: If True, simulate without actually retrying
        retry_only_retryable: If True, only retry retryable failures
        
    Returns:
        Summary of the retry operation with detailed safety information
    """
    registry = FailedJobRegistry(queue=q)
    job_ids = registry.get_job_ids()
    
    requeued = []
    skipped_non_retryable = []
    skipped_policy = []
    errors = []
    
    for job_id in job_ids:
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            
            # Classify failure
            exc_info = job.exc_info or ""
            should_retry, failure_type = failure_classifier.should_retry_failure(exc_info)
            
            # Check if retryable
            if retry_only_retryable and not should_retry:
                skipped_non_retryable.append({
                    "job_id": job_id,
                    "failure_type": failure_type.value,
                    "reason": "non_retryable"
                })
                logger.info(f"Skipping non-retryable job {job_id} ({failure_type.value})")
                continue
            
            # Check retry policy
            can_retry, reason = retry_policy.can_retry(job)
            
            if not can_retry:
                skipped_policy.append({
                    "job_id": job_id,
                    "failure_type": failure_type.value,
                    "reason": reason
                })
                logger.info(f"Skipping job {job_id} due to policy: {reason}")
                continue
            
            # Dry run
            if dry_run:
                audit_logger.log_dry_run(
                    job=job,
                    retry_reason="batch_retry",
                    failure_type=failure_type.value
                )
                requeued.append(job_id)
                continue
            
            # Record retry attempt
            retry_policy.record_retry_attempt(job)
            
            # Log to audit
            audit_logger.log_retry_attempt(
                job=job,
                retry_reason="batch_retry",
                failure_type=failure_type.value,
                dry_run=False
            )
            
            # Requeue
            registry.requeue(job_id)
            requeued.append(job_id)
            logger.info(f"Requeued job {job_id}")
            
        except Exception as e:
            error_msg = str(e)
            errors.append({
                "job_id": job_id,
                "error": error_msg
            })
            logger.error(f"Error processing job {job_id}: {error_msg}")
    
    # Flush audit logs
    audit_logger.flush()
    
    return {
        "success": len(errors) == 0,
        "dry_run": dry_run,
        "total_failed": len(job_ids),
        "requeued_count": len(requeued),
        "skipped_non_retryable_count": len(skipped_non_retryable),
        "skipped_policy_count": len(skipped_policy),
        "error_count": len(errors),
        "requeued_jobs": requeued,
        "skipped_non_retryable": skipped_non_retryable,
        "skipped_policy": skipped_policy,
        "errors": errors
    }


@router.delete("/failed/{job_id}")
def delete_failed_job(job_id: str) -> Dict[str, Any]:
    """
    Delete a specific failed job from the registry.
    
    Args:
        job_id: The ID of the job to delete
        
    Returns:
        Status of the delete operation
    """
    try:
        registry = FailedJobRegistry(queue=q)
        
        if job_id not in registry.get_job_ids():
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found in failed jobs registry"
            )
        
        # Remove from registry
        registry.remove(job_id)
        
        # Also delete the job itself
        job = Job.fetch(job_id, connection=redis_conn)
        job.delete()
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Job {job_id} has been deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete job {job_id}: {str(e)}"
        )


@router.delete("/failed/clear")
def clear_failed_jobs() -> Dict[str, Any]:
    """
    Clear all failed jobs from the registry.
    
    Returns:
        Summary of the clear operation
    """
    registry = FailedJobRegistry(queue=q)
    job_ids = registry.get_job_ids()
    
    deleted = []
    errors = []
    
    for job_id in job_ids:
        try:
            registry.remove(job_id)
            job = Job.fetch(job_id, connection=redis_conn)
            job.delete()
            deleted.append(job_id)
        except Exception as e:
            errors.append({
                "job_id": job_id,
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "total_failed": len(job_ids),
        "deleted_count": len(deleted),
        "error_count": len(errors),
        "deleted_jobs": deleted,
        "errors": errors
    }


@router.get("/status/{job_id}")
def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status and details of a specific job.
    
    Args:
        job_id: The ID of the job
        
    Returns:
        Job status and details
    """
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        
        return {
            "job_id": job.id,
            "status": job.get_status(),
            "func_name": job.func_name,
            "args": job.args,
            "kwargs": job.kwargs,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
            "result": str(job.result) if job.result else None,
            "exc_info": job.exc_info if job.is_failed else None,
            "is_finished": job.is_finished,
            "is_failed": job.is_failed,
            "is_started": job.is_started,
            "is_queued": job.is_queued,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found: {str(e)}"
        )


@router.get("/stats")
def get_queue_stats() -> Dict[str, Any]:
    """
    Get statistics about the job queue including retry information.
    
    Returns:
        Queue statistics including job counts by status and retry stats
    """
    try:
        failed_registry = FailedJobRegistry(queue=q)
        started_registry = StartedJobRegistry(queue=q)
        finished_registry = FinishedJobRegistry(queue=q)
        
        # Get retry audit stats
        retry_stats = audit_logger.get_retry_stats()
        
        return {
            "queue_name": q.name,
            "queued_count": len(q),
            "failed_count": len(failed_registry),
            "started_count": len(started_registry),
            "finished_count": len(finished_registry),
            "retry_stats": retry_stats,
        }
        
    except Exception as e:
        logger.error(f"Error getting queue stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue stats: {str(e)}"
        )


@router.get("/retry-audit")
def get_retry_audit(
    job_id: Optional[str] = Query(None, description="Filter by job ID"),
    limit: int = Query(100, description="Maximum number of records to return")
) -> Dict[str, Any]:
    """
    Get retry audit history.
    
    Args:
        job_id: Optional job ID to filter by
        limit: Maximum number of records to return
        
    Returns:
        Retry audit records
    """
    try:
        df = audit_logger.get_audit_history(job_id=job_id)
        
        if df.empty:
            return {
                "total_records": 0,
                "records": []
            }
        
        # Limit results
        df = df.head(limit)
        
        # Convert to dict
        records = df.to_dict('records')
        
        return {
            "total_records": len(df),
            "records": records
        }
        
    except Exception as e:
        logger.error(f"Error getting retry audit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get retry audit: {str(e)}"
        )
