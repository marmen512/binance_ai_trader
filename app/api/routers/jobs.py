"""
Jobs management API router.

Provides endpoints to manage RQ jobs including viewing and retrying failed jobs.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import FailedJobRegistry, StartedJobRegistry, FinishedJobRegistry
from app.core.config import settings

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
redis_conn = Redis.from_url(settings.REDIS_URL)
q = Queue(connection=redis_conn)


@router.get("/failed")
def list_failed_jobs() -> List[Dict[str, Any]]:
    """
    List all failed jobs in the queue.
    
    Returns:
        List of failed jobs with their details
    """
    registry = FailedJobRegistry(queue=q)
    failed_jobs = []
    
    for job_id in registry.get_job_ids():
        try:
            job = Job.fetch(job_id, connection=redis_conn)
            failed_jobs.append({
                "job_id": job.id,
                "func_name": job.func_name,
                "args": job.args,
                "kwargs": job.kwargs,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "ended_at": job.ended_at.isoformat() if job.ended_at else None,
                "exc_info": job.exc_info,
                "result": str(job.result) if job.result else None,
            })
        except Exception as e:
            failed_jobs.append({
                "job_id": job_id,
                "error": f"Failed to fetch job details: {str(e)}"
            })
    
    return failed_jobs


@router.post("/failed/{job_id}/retry")
def retry_failed_job(job_id: str) -> Dict[str, Any]:
    """
    Retry a specific failed job.
    
    Args:
        job_id: The ID of the job to retry
        
    Returns:
        Status of the retry operation
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
        
        # Requeue the job
        registry.requeue(job_id)
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"Job {job_id} has been requeued successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry job {job_id}: {str(e)}"
        )


@router.post("/failed/retry-all")
def retry_all_failed_jobs() -> Dict[str, Any]:
    """
    Retry all failed jobs in the queue.
    
    Returns:
        Summary of the retry operation
    """
    registry = FailedJobRegistry(queue=q)
    job_ids = registry.get_job_ids()
    
    requeued = []
    errors = []
    
    for job_id in job_ids:
        try:
            registry.requeue(job_id)
            requeued.append(job_id)
        except Exception as e:
            errors.append({
                "job_id": job_id,
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "total_failed": len(job_ids),
        "requeued_count": len(requeued),
        "error_count": len(errors),
        "requeued_jobs": requeued,
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
    Get statistics about the job queue.
    
    Returns:
        Queue statistics including job counts by status
    """
    try:
        failed_registry = FailedJobRegistry(queue=q)
        started_registry = StartedJobRegistry(queue=q)
        finished_registry = FinishedJobRegistry(queue=q)
        
        return {
            "queue_name": q.name,
            "queued_count": len(q),
            "failed_count": len(failed_registry),
            "started_count": len(started_registry),
            "finished_count": len(finished_registry),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue stats: {str(e)}"
        )
