from importlib.metadata import version
import logging

VERSION = version("controller-companion")
logging.basicConfig()
logger = logging.getLogger()
