"""
Retry audit logger for tracking all retry operations.

Logs all retry attempts to parquet files for audit trail and analysis.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import pandas as pd
from dataclasses import dataclass, asdict
from rq.job import Job

logger = logging.getLogger(__name__)


@dataclass
class RetryAuditRecord:
    """Audit record for a retry operation."""
    job_id: str
    timestamp: str
    user_or_system: str
    retry_reason: str
    attempt_number: int
    failure_type: str
    dry_run_flag: bool
    func_name: str
    job_args: str
    job_kwargs: str
    idempotency_key: Optional[str] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None


class RetryAuditLogger:
    """
    Logger for audit trail of job retry operations.
    
    Writes audit records to sharded parquet files.
    """
    
    def __init__(self, log_dir: str = "logs/job_retry_audit"):
        """
        Initialize retry audit logger.
        
        Args:
            log_dir: Directory for audit log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._buffer = []
        self._buffer_size = 100  # Flush after 100 records
    
    def _get_log_file_path(self, date: datetime) -> Path:
        """
        Get the log file path for a given date.
        
        Args:
            date: Date for the log file
            
        Returns:
            Path to the log file
        """
        filename = f"retry_audit_{date.strftime('%Y%m%d')}.parquet"
        return self.log_dir / filename
    
    def log_retry_attempt(
        self,
        job: Job,
        retry_reason: str,
        failure_type: str,
        dry_run: bool = False,
        user_or_system: str = "system",
        success: Optional[bool] = None,
        error_message: Optional[str] = None
    ):
        """
        Log a retry attempt.
        
        Args:
            job: RQ Job instance
            retry_reason: Reason for retry
            failure_type: Type of failure (from FailureClassifier)
            dry_run: Whether this is a dry run
            user_or_system: Who initiated the retry
            success: Whether retry was successful (None if not yet completed)
            error_message: Error message if retry failed
        """
        now = datetime.now()
        
        # Get retry metadata
        attempt_number = job.meta.get('retry_attempts', 0)
        idempotency_key = job.meta.get('idempotency_key')
        
        # Create audit record
        record = RetryAuditRecord(
            job_id=job.id,
            timestamp=now.isoformat(),
            user_or_system=user_or_system,
            retry_reason=retry_reason,
            attempt_number=attempt_number,
            failure_type=failure_type,
            dry_run_flag=dry_run,
            func_name=job.func_name,
            job_args=str(job.args),
            job_kwargs=str(job.kwargs),
            idempotency_key=idempotency_key,
            success=success,
            error_message=error_message
        )
        
        # Add to buffer
        self._buffer.append(record)
        
        logger.info(
            f"Logged retry audit: job={job.id}, attempt={attempt_number}, "
            f"reason={retry_reason}, dry_run={dry_run}"
        )
        
        # Flush if buffer is full
        if len(self._buffer) >= self._buffer_size:
            self.flush()
    
    def flush(self):
        """Flush buffered records to parquet file."""
        if not self._buffer:
            return
        
        try:
            # Convert records to DataFrame
            records_dict = [asdict(r) for r in self._buffer]
            df = pd.DataFrame(records_dict)
            
            # Group by date
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            
            for date, group_df in df.groupby('date'):
                log_file = self._get_log_file_path(datetime.combine(date, datetime.min.time()))
                
                # Append to existing file or create new
                if log_file.exists():
                    existing_df = pd.read_parquet(log_file)
                    combined_df = pd.concat([existing_df, group_df.drop('date', axis=1)], ignore_index=True)
                else:
                    combined_df = group_df.drop('date', axis=1)
                
                # Write to parquet
                combined_df.to_parquet(log_file, index=False)
                logger.info(f"Flushed {len(group_df)} audit records to {log_file}")
            
            # Clear buffer
            self._buffer = []
            
        except Exception as e:
            logger.error(f"Error flushing audit records: {str(e)}", exc_info=True)
    
    def log_dry_run(
        self,
        job: Job,
        retry_reason: str,
        failure_type: str,
        user_or_system: str = "user"
    ):
        """
        Log a dry run retry attempt.
        
        Args:
            job: RQ Job instance
            retry_reason: Reason for retry
            failure_type: Type of failure
            user_or_system: Who initiated the dry run
        """
        self.log_retry_attempt(
            job=job,
            retry_reason=retry_reason,
            failure_type=failure_type,
            dry_run=True,
            user_or_system=user_or_system
        )
    
    def get_audit_history(
        self,
        job_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get audit history from parquet files.
        
        Args:
            job_id: Optional job ID to filter by
            start_date: Optional start date for filter
            end_date: Optional end date for filter
            
        Returns:
            DataFrame with audit records
        """
        all_records = []
        
        # Get all parquet files
        parquet_files = sorted(self.log_dir.glob("retry_audit_*.parquet"))
        
        for file_path in parquet_files:
            try:
                df = pd.read_parquet(file_path)
                all_records.append(df)
            except Exception as e:
                logger.error(f"Error reading {file_path}: {str(e)}")
        
        if not all_records:
            return pd.DataFrame()
        
        # Combine all records
        combined_df = pd.concat(all_records, ignore_index=True)
        
        # Apply filters
        if job_id:
            combined_df = combined_df[combined_df['job_id'] == job_id]
        
        if start_date:
            combined_df = combined_df[
                pd.to_datetime(combined_df['timestamp']) >= start_date
            ]
        
        if end_date:
            combined_df = combined_df[
                pd.to_datetime(combined_df['timestamp']) <= end_date
            ]
        
        return combined_df
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about retry operations.
        
        Returns:
            Dictionary with retry statistics
        """
        df = self.get_audit_history()
        
        if df.empty:
            return {
                'total_retries': 0,
                'successful_retries': 0,
                'failed_retries': 0,
                'dry_runs': 0,
            }
        
        stats = {
            'total_retries': len(df),
            'successful_retries': len(df[df['success'] == True]),
            'failed_retries': len(df[df['success'] == False]),
            'dry_runs': len(df[df['dry_run_flag'] == True]),
            'unique_jobs': df['job_id'].nunique(),
            'failure_types': df['failure_type'].value_counts().to_dict(),
        }
        
        return stats
    
    def __del__(self):
        """Flush on cleanup."""
        self.flush()
