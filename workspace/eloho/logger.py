import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_dir: Path = None):
    logger.remove()

    # Console: minimal
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm}</green>|<level>{level}</level>|{message}",
        level="INFO",
        colorize=True,
    )

    # File: detailed
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_dir / "eloho.log",
            format="{time:YYYY-MM-DD HH:mm:ss}|{level}|{function}:{line}|{message}",
            level="DEBUG",
            rotation="10 MB",
            retention="30 days",
        )
