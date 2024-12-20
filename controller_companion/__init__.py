from importlib.metadata import version
from pathlib import Path

APP_NAME = "Controller Companion"
VERSION = f'v{version("controller-companion")}'
PACKAGE_DIR = Path(__file__).parent.absolute()
