import logging
from rich.logging import RichHandler

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR

FORMAT = "%(message)s"
logging.basicConfig(format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger(__name__)


def set_log_level(level):
    logger.setLevel(level)
