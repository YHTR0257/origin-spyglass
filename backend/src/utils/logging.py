import logging
import os
import sys


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("origin_spyglass")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
