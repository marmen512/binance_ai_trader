#!/usr/bin/env python3
"""
Chaos Test: Kill Redis Simulation

Simulates Redis crash during critical operations to test:
- Idempotency guard resilience
- Recovery behavior
- Error handling
- Side effect protection

Usage:
    python scripts/chaos/kill_redis_test.py
"""

import sys
import os
import time
import logging
from typing import Optional
import redis
from redis.exceptions import ConnectionError, TimeoutError

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.idempotency.side_effect_wrapper import SideEffectWrapper, SideEffectType
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class RedisKillSimulator:
    """Simulates Redis crash scenarios"""
    
    def __init__(self, redis_url: str):
        """Initialize simulator"""
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.reconnect()
    
    def reconnect(self) -> bool:
        """Attempt to reconnect to Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            self.redis_client.ping()
            logger.info("✓ Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            return False
    
    def simulate_crash_during_operation(self) -> None:
        """Simulate Redis crash during a critical operation"""
        logger.info("\n" + "="*60)
        logger.info("TEST: Redis crash during critical operation")
        logger.info("="*60)
        
        if not self.redis_client:
            logger.error("No Redis connection available")
            return
        
        wrapper = SideEffectWrapper(self.redis_client)
        
        # Test case 1: Operation succeeds before crash
        logger.info("\n[Test 1] Operation before crash:")
        entity_id = "test_order_1"
        
        def mock_order_placement():
            logger.info("  → Placing order...")
            time.sleep(0.1)
            return {"order_id": "12345", "status": "filled"}
        
        try:
            executed, result = wrapper.execute_once(
                SideEffectType.ORDER_PLACEMENT,
                entity_id,
                mock_order_placement
            )
            logger.info(f"  ✓ First execution: executed={executed}, result={result}")
        except Exception as e:
            logger.error(f"  ✗ Operation failed: {e}")
        
        # Simulate Redis becoming unavailable
        logger.info("\n[Simulating Redis crash]")
        logger.warning("  ⚠ Redis connection will be terminated")
        
        try:
            # Close connection pool to simulate crash
            if hasattr(self.redis_client, 'connection_pool'):
                self.redis_client.connection_pool.disconnect()
            logger.info("  → Redis connection terminated")
        except Exception as e:
            logger.error(f"  Failed to simulate crash: {e}")
        
        # Test case 2: Retry after crash
        logger.info("\n[Test 2] Retry after crash:")
        time.sleep(1)
        
        try:
            # This should fail due to Redis being down
            executed, result = wrapper.execute_once(
                SideEffectType.ORDER_PLACEMENT,
                entity_id,
                mock_order_placement
            )
            logger.info(f"  Unexpected success: executed={executed}, result={result}")
        except (ConnectionError, TimeoutError) as e:
            logger.info(f"  ✓ Expected failure (Redis down): {e.__class__.__name__}")
        except Exception as e:
            logger.error(f"  ✗ Unexpected error: {e}")
        
        # Test case 3: Recovery
        logger.info("\n[Test 3] Recovery after reconnect:")
        if self.reconnect():
            wrapper = SideEffectWrapper(self.redis_client)
            
            try:
                # This should skip execution (already executed)
                executed, result = wrapper.execute_once(
                    SideEffectType.ORDER_PLACEMENT,
                    entity_id,
                    mock_order_placement
                )
                logger.info(f"  ✓ After recovery: executed={executed} (should be False)")
                logger.info(f"  ✓ Cached result: {result}")
                
                if not executed:
                    logger.info("  ✓ SUCCESS: Idempotency preserved across Redis crash!")
                else:
                    logger.error("  ✗ FAILURE: Operation re-executed (duplicate side effect)")
            except Exception as e:
                logger.error(f"  ✗ Recovery failed: {e}")
    
    def simulate_intermittent_failures(self) -> None:
        """Simulate intermittent Redis failures"""
        logger.info("\n" + "="*60)
        logger.info("TEST: Intermittent Redis failures")
        logger.info("="*60)
        
        if not self.redis_client:
            logger.error("No Redis connection available")
            return
        
        wrapper = SideEffectWrapper(self.redis_client)
        
        # Simulate multiple retries with intermittent failures
        for i in range(3):
            logger.info(f"\n[Attempt {i+1}]")
            entity_id = f"test_order_{i+1}"
            
            def mock_operation():
                logger.info("  → Executing operation...")
                return {"success": True, "attempt": i+1}
            
            try:
                executed, result = wrapper.execute_once(
                    SideEffectType.ORDER_PLACEMENT,
                    entity_id,
                    mock_operation
                )
                logger.info(f"  ✓ executed={executed}, result={result}")
                
                # Simulate intermittent disconnection
                if i == 1:
                    logger.warning("  ⚠ Simulating brief disconnection...")
                    if hasattr(self.redis_client, 'connection_pool'):
                        self.redis_client.connection_pool.disconnect()
                    time.sleep(0.5)
                    self.reconnect()
                    wrapper = SideEffectWrapper(self.redis_client)
            except Exception as e:
                logger.error(f"  ✗ Operation failed: {e}")
            
            time.sleep(0.5)
    
    def run_all_tests(self) -> None:
        """Run all chaos tests"""
        logger.info("\n" + "="*80)
        logger.info("REDIS KILL CHAOS TEST")
        logger.info("="*80)
        
        self.simulate_crash_during_operation()
        time.sleep(2)
        self.simulate_intermittent_failures()
        
        logger.info("\n" + "="*80)
        logger.info("CHAOS TEST COMPLETE")
        logger.info("="*80)
        logger.info("\nReview the results above to verify:")
        logger.info("  1. Operations fail gracefully when Redis is down")
        logger.info("  2. Idempotency is preserved after Redis recovery")
        logger.info("  3. No duplicate side effects occur")


def main():
    """Main entry point"""
    logger.info("Starting Redis kill chaos test...")
    
    simulator = RedisKillSimulator(settings.REDIS_URL)
    
    if not simulator.redis_client:
        logger.error("Failed to connect to Redis. Is Redis running?")
        sys.exit(1)
    
    try:
        simulator.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
