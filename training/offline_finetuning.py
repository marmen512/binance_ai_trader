"""
OFFLINE FINETUNING ENTRYPOINT.

WARNING:
- MUST NOT be imported during paper trading
- Manual execution only
"""

from core.logging import setup_logger
from training.offline_finetuning_core import fine_tune_pass

logger = setup_logger("offline_finetuning")


def main():
    logger.info("Offline finetuning entrypoint loaded")
    logger.info("Use fine_tune_pass() explicitly")
    

if __name__ == "__main__":
    main()
