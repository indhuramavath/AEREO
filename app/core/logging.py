import logging
import sys


def setup_logging(debug: bool = False) -> logging.Logger:
    log_level = logging.DEBUG if debug else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(log_level)

    logger = logging.getLogger("aereo_api")
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers if setup is invoked multiple times
    if not logger.handlers:
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_logging()
