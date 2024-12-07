from pathlib import Path
import sys
from typing import Union


def __get_resource_path(relative_path: Union[Path, str]) -> Path:
    """Get correct path to resource, works for dev and for executables.

    Args:
        relative_path (str): Path relative to the project root.

    Returns:
        Path: Full path to the requested resource.
    """
    # for executables, _MEIPASS is set, in dev mode we will use the repo root.
    base_path = getattr(sys, "_MEIPASS", "")
    return Path(base_path, relative_path)


def is_frozen() -> bool:
    if getattr(sys, "frozen", False):
        # we are running in a bundle
        return True
    return False


def get_executable_path() -> Path:
    return Path(sys.executable)


APP_ICON_ICO = __get_resource_path("controller_companion/res/app.ico")
APP_ICON_PNG = __get_resource_path("controller_companion/res/app.png")
