"""
OFFLINE FINETUNING ENTRYPOINT.

WARNING:
- This module MUST NOT be imported during paper trading
- This module is executed manually only
- No live / replay / CI code should depend on it
"""

from core.logging import setup_logger

logger = setup_logger("offline_finetuning")


def fine_tune_pass(*args, **kwargs):
    """
    TEMPORARY STUB.

    Real training implementation will be added later.
    This stub exists ONLY to prevent circular imports and crashes.
    """
    logger.warning(
        "fine_tune_pass() is a stub. Offline training is not yet implemented."
    )
    raise NotImplementedError(
        "Offline fine-tuning core not implemented yet"
    )


def main():
    logger.info("Offline finetuning entrypoint loaded")
    logger.info("Nothing executed automatically")


if __name__ == "__main__":
    main()
