"""
Tests for jobs management API.

Tests the functionality of listing, retrying, and managing failed jobs.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app

client = TestClient(app)


class TestJobsAPI:
    """Test jobs management endpoints."""
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.FailedJobRegistry')
    def test_list_failed_jobs_empty(self, mock_registry_class, mock_queue_class, mock_redis):
        """Test listing failed jobs when there are none."""
        mock_registry = MagicMock()
        mock_registry.get_job_ids.return_value = []
        mock_registry_class.return_value = mock_registry
        
        response = client.get("/api/v1/jobs/failed")
        
        assert response.status_code == 200
        assert response.json() == []
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.FailedJobRegistry')
    @patch('app.api.routers.jobs.Job')
    def test_list_failed_jobs_with_jobs(self, mock_job_class, mock_registry_class, mock_queue_class, mock_redis):
        """Test listing failed jobs when there are some."""
        mock_registry = MagicMock()
        mock_registry.get_job_ids.return_value = ['job-123']
        mock_registry_class.return_value = mock_registry
        
        mock_job = MagicMock()
        mock_job.id = 'job-123'
        mock_job.func_name = 'test_function'
        mock_job.args = [1, 2]
        mock_job.kwargs = {'key': 'value'}
        mock_job.created_at = None
        mock_job.ended_at = None
        mock_job.exc_info = 'Error message'
        mock_job.result = None
        mock_job_class.fetch.return_value = mock_job
        
        response = client.get("/api/v1/jobs/failed")
        
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]['job_id'] == 'job-123'
        assert jobs[0]['func_name'] == 'test_function'
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.FailedJobRegistry')
    @patch('app.api.routers.jobs.Job')
    def test_retry_failed_job_success(self, mock_job_class, mock_registry_class, mock_queue_class, mock_redis):
        """Test successfully retrying a failed job."""
        mock_registry = MagicMock()
        mock_registry.get_job_ids.return_value = ['job-123']
        mock_registry_class.return_value = mock_registry
        
        mock_job = MagicMock()
        mock_job_class.fetch.return_value = mock_job
        
        response = client.post("/api/v1/jobs/failed/job-123/retry")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['job_id'] == 'job-123'
        mock_registry.requeue.assert_called_once_with('job-123')
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.FailedJobRegistry')
    @patch('app.api.routers.jobs.Job')
    def test_retry_failed_job_not_found(self, mock_job_class, mock_registry_class, mock_queue_class, mock_redis):
        """Test retrying a job that doesn't exist in failed registry."""
        mock_registry = MagicMock()
        mock_registry.get_job_ids.return_value = []
        mock_registry_class.return_value = mock_registry
        
        mock_job = MagicMock()
        mock_job_class.fetch.return_value = mock_job
        
        response = client.post("/api/v1/jobs/failed/job-999/retry")
        
        assert response.status_code == 404
        assert "not found in failed jobs registry" in response.json()['detail']
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.FailedJobRegistry')
    def test_retry_all_failed_jobs_success(self, mock_registry_class, mock_queue_class, mock_redis):
        """Test retrying all failed jobs."""
        mock_registry = MagicMock()
        mock_registry.get_job_ids.return_value = ['job-1', 'job-2', 'job-3']
        mock_registry_class.return_value = mock_registry
        
        response = client.post("/api/v1/jobs/failed/retry-all")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['total_failed'] == 3
        assert data['requeued_count'] == 3
        assert data['error_count'] == 0
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.FailedJobRegistry')
    @patch('app.api.routers.jobs.Job')
    def test_delete_failed_job_success(self, mock_job_class, mock_registry_class, mock_queue_class, mock_redis):
        """Test deleting a failed job."""
        mock_registry = MagicMock()
        mock_registry.get_job_ids.return_value = ['job-123']
        mock_registry_class.return_value = mock_registry
        
        mock_job = MagicMock()
        mock_job_class.fetch.return_value = mock_job
        
        response = client.delete("/api/v1/jobs/failed/job-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['job_id'] == 'job-123'
        mock_registry.remove.assert_called_once_with('job-123')
        mock_job.delete.assert_called_once()
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.FailedJobRegistry')
    def test_clear_failed_jobs(self, mock_registry_class, mock_queue_class, mock_redis):
        """Test clearing all failed jobs."""
        mock_registry = MagicMock()
        mock_registry.get_job_ids.return_value = ['job-1', 'job-2']
        mock_registry_class.return_value = mock_registry
        
        mock_job1 = MagicMock()
        mock_job2 = MagicMock()
        
        with patch('app.api.routers.jobs.Job') as mock_job_class:
            mock_job_class.fetch.side_effect = [mock_job1, mock_job2]
            
            response = client.delete("/api/v1/jobs/failed/clear")
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['total_failed'] == 2
            assert data['deleted_count'] == 2
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.Job')
    def test_get_job_status(self, mock_job_class, mock_queue_class, mock_redis):
        """Test getting job status."""
        mock_job = MagicMock()
        mock_job.id = 'job-123'
        mock_job.get_status.return_value = 'finished'
        mock_job.func_name = 'test_func'
        mock_job.args = []
        mock_job.kwargs = {}
        mock_job.created_at = None
        mock_job.started_at = None
        mock_job.ended_at = None
        mock_job.result = 'success'
        mock_job.is_finished = True
        mock_job.is_failed = False
        mock_job.is_started = False
        mock_job.is_queued = False
        mock_job_class.fetch.return_value = mock_job
        
        response = client.get("/api/v1/jobs/status/job-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data['job_id'] == 'job-123'
        assert data['status'] == 'finished'
        assert data['is_finished'] is True
    
    @patch('app.api.routers.jobs.redis_conn')
    @patch('app.api.routers.jobs.Queue')
    @patch('app.api.routers.jobs.FailedJobRegistry')
    @patch('app.api.routers.jobs.StartedJobRegistry')
    @patch('app.api.routers.jobs.FinishedJobRegistry')
    def test_get_queue_stats(self, mock_finished_reg, mock_started_reg, mock_failed_reg, mock_queue_class, mock_redis):
        """Test getting queue statistics."""
        mock_queue = MagicMock()
        mock_queue.name = 'default'
        mock_queue.__len__ = MagicMock(return_value=5)
        mock_queue_class.return_value = mock_queue
        
        mock_failed_reg.return_value.__len__ = MagicMock(return_value=2)
        mock_started_reg.return_value.__len__ = MagicMock(return_value=1)
        mock_finished_reg.return_value.__len__ = MagicMock(return_value=10)
        
        with patch('app.api.routers.jobs.q', mock_queue):
            response = client.get("/api/v1/jobs/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data['queue_name'] == 'default'
        assert data['queued_count'] == 5
        assert data['failed_count'] == 2
        assert data['started_count'] == 1
        assert data['finished_count'] == 10
