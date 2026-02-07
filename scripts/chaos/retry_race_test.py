#!/usr/bin/env python3
"""
Chaos Test: Retry Race Condition Simulation

Simulates worker race conditions to test:
- Idempotency under concurrent retries
- Lock contention handling
- Duplicate side effect prevention
- Result caching consistency

Usage:
    python scripts/chaos/retry_race_test.py
"""

import sys
import os
import time
import logging
import threading
from typing import List, Dict, Any
import redis

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.idempotency.side_effect_wrapper import SideEffectWrapper, SideEffectType
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(threadName)-10s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class RetryRaceSimulator:
    """Simulates concurrent worker retry scenarios"""
    
    def __init__(self, redis_url: str):
        """Initialize simulator"""
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        self.execution_count = 0
        self.lock = threading.Lock()
        self.results: List[Dict[str, Any]] = []
    
    def mock_order_placement(self, thread_id: int, entity_id: str) -> Dict[str, Any]:
        """Mock order placement with execution tracking"""
        with self.lock:
            self.execution_count += 1
            count = self.execution_count
        
        logger.info(f"Thread-{thread_id}: Executing order placement (execution #{count})")
        time.sleep(0.1)  # Simulate work
        
        result = {
            "order_id": f"order_{entity_id}",
            "thread": thread_id,
            "execution_number": count,
            "timestamp": time.time()
        }
        
        return result
    
    def worker_thread(self, thread_id: int, entity_id: str, delay: float = 0) -> None:
        """Worker thread that attempts to execute a side effect"""
        time.sleep(delay)  # Stagger start times
        
        logger.info(f"Thread-{thread_id}: Starting")
        
        try:
            wrapper = SideEffectWrapper(self.redis_client)
            
            executed, result = wrapper.execute_once(
                SideEffectType.ORDER_PLACEMENT,
                entity_id,
                lambda: self.mock_order_placement(thread_id, entity_id)
            )
            
            thread_result = {
                "thread_id": thread_id,
                "executed": executed,
                "result": result,
                "success": True
            }
            
            if executed:
                logger.info(f"Thread-{thread_id}: ✓ Operation executed")
            else:
                logger.info(f"Thread-{thread_id}: ⊘ Operation skipped (already executed)")
            
            with self.lock:
                self.results.append(thread_result)
                
        except Exception as e:
            logger.error(f"Thread-{thread_id}: ✗ Failed with error: {e}")
            with self.lock:
                self.results.append({
                    "thread_id": thread_id,
                    "executed": False,
                    "result": None,
                    "success": False,
                    "error": str(e)
                })
    
    def test_concurrent_execution(self, num_workers: int = 5) -> None:
        """Test concurrent execution of same operation"""
        logger.info("\n" + "="*60)
        logger.info(f"TEST: Concurrent execution with {num_workers} workers")
        logger.info("="*60)
        
        # Reset counters
        self.execution_count = 0
        self.results = []
        
        entity_id = "test_concurrent_order"
        
        # Clean up previous test data
        wrapper = SideEffectWrapper(self.redis_client)
        wrapper.clear(SideEffectType.ORDER_PLACEMENT, entity_id)
        
        # Start worker threads
        threads = []
        for i in range(num_workers):
            thread = threading.Thread(
                target=self.worker_thread,
                args=(i, entity_id, 0),
                name=f"Worker-{i}"
            )
            threads.append(thread)
        
        logger.info(f"Starting {num_workers} concurrent workers...")
        start_time = time.time()
        
        # Start all threads simultaneously
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        duration = time.time() - start_time
        
        # Analyze results
        logger.info("\n" + "-"*60)
        logger.info("RESULTS:")
        logger.info("-"*60)
        
        executed_count = sum(1 for r in self.results if r.get("executed", False))
        skipped_count = sum(1 for r in self.results if not r.get("executed", False) and r.get("success", False))
        failed_count = sum(1 for r in self.results if not r.get("success", False))
        
        logger.info(f"Total workers: {num_workers}")
        logger.info(f"Operations executed: {executed_count}")
        logger.info(f"Operations skipped: {skipped_count}")
        logger.info(f"Operations failed: {failed_count}")
        logger.info(f"Total executions: {self.execution_count}")
        logger.info(f"Duration: {duration:.2f}s")
        
        # Validate
        if self.execution_count == 1 and executed_count == 1:
            logger.info("\n✓ SUCCESS: Exactly one execution (idempotency working!)")
        else:
            logger.error(f"\n✗ FAILURE: Expected 1 execution, got {self.execution_count}")
    
    def test_staggered_retries(self, num_workers: int = 3) -> None:
        """Test staggered retry attempts"""
        logger.info("\n" + "="*60)
        logger.info(f"TEST: Staggered retries with {num_workers} workers")
        logger.info("="*60)
        
        # Reset counters
        self.execution_count = 0
        self.results = []
        
        entity_id = "test_staggered_order"
        
        # Clean up previous test data
        wrapper = SideEffectWrapper(self.redis_client)
        wrapper.clear(SideEffectType.ORDER_PLACEMENT, entity_id)
        
        # Start worker threads with staggered delays
        threads = []
        for i in range(num_workers):
            delay = i * 0.5  # 500ms between each worker
            thread = threading.Thread(
                target=self.worker_thread,
                args=(i, entity_id, delay),
                name=f"Worker-{i}"
            )
            threads.append(thread)
        
        logger.info(f"Starting {num_workers} workers with staggered delays...")
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        logger.info("\n" + "-"*60)
        logger.info("RESULTS:")
        logger.info("-"*60)
        
        executed_count = sum(1 for r in self.results if r.get("executed", False))
        
        logger.info(f"Total workers: {num_workers}")
        logger.info(f"Operations executed: {executed_count}")
        logger.info(f"Total executions: {self.execution_count}")
        
        # Validate
        if self.execution_count == 1 and executed_count == 1:
            logger.info("\n✓ SUCCESS: Exactly one execution with staggered retries!")
        else:
            logger.error(f"\n✗ FAILURE: Expected 1 execution, got {self.execution_count}")
    
    def test_burst_retries(self, num_bursts: int = 3, burst_size: int = 3) -> None:
        """Test burst retry patterns"""
        logger.info("\n" + "="*60)
        logger.info(f"TEST: Burst retries ({num_bursts} bursts of {burst_size} workers)")
        logger.info("="*60)
        
        for burst_num in range(num_bursts):
            logger.info(f"\n[Burst {burst_num + 1}]")
            
            # Reset counters for this burst
            self.execution_count = 0
            self.results = []
            
            entity_id = f"test_burst_order_{burst_num}"
            
            # Start burst of workers
            threads = []
            for i in range(burst_size):
                thread = threading.Thread(
                    target=self.worker_thread,
                    args=(i, entity_id, 0),
                    name=f"Burst{burst_num}-Worker-{i}"
                )
                threads.append(thread)
            
            # Start all threads
            for thread in threads:
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            executed_count = sum(1 for r in self.results if r.get("executed", False))
            
            logger.info(f"Burst {burst_num + 1}: {executed_count} executions")
            
            if self.execution_count != 1:
                logger.error(f"✗ Burst {burst_num + 1} failed: {self.execution_count} executions")
            
            time.sleep(0.5)  # Pause between bursts
        
        logger.info("\n✓ All bursts completed")
    
    def run_all_tests(self) -> None:
        """Run all race condition tests"""
        logger.info("\n" + "="*80)
        logger.info("RETRY RACE CONDITION CHAOS TEST")
        logger.info("="*80)
        
        self.test_concurrent_execution(num_workers=5)
        time.sleep(1)
        
        self.test_staggered_retries(num_workers=3)
        time.sleep(1)
        
        self.test_burst_retries(num_bursts=3, burst_size=3)
        
        logger.info("\n" + "="*80)
        logger.info("CHAOS TEST COMPLETE")
        logger.info("="*80)


def main():
    """Main entry point"""
    logger.info("Starting retry race chaos test...")
    
    try:
        simulator = RetryRaceSimulator(settings.REDIS_URL)
        simulator.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
