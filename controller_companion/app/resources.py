from pathlib import Path
import sys
from typing import Union

from controller_companion import PACKAGE_DIR


def __get_resource_path(relative_path: Union[Path, str]) -> Path:
    """Get correct path to resource, works for dev and for executables.

    Args:
        relative_path (str): Path relative to the project root.

    Returns:
        Path: Full path to the requested resource.
    """
    # for executables, _MEIPASS is set, in dev mode we will use the repo root.
    base_path = getattr(sys, "_MEIPASS", PACKAGE_DIR.parent)
    return Path(base_path, relative_path)


def is_frozen() -> bool:
    if getattr(sys, "frozen", False):
        # we are running in a bundle
        return True
    return False


def get_executable_path() -> Path:
    return Path(sys.executable)


APP_ICON_PNG = __get_resource_path("controller_companion/app/res/app.png")
APP_ICON_PNG_TRAY_32 = __get_resource_path(
    "controller_companion/app/res/tray_icon_32.png"
)
APP_ICON_PNG_TRAY_32_DARK = __get_resource_path(
    "controller_companion/app/res/tray_icon_dark_32.png"
)
APP_ICON_PNG_TRAY_16 = __get_resource_path(
    "controller_companion/app/res/tray_icon_16.png"
)
APP_ICON_PNG_TRAY_16_DARK = __get_resource_path(
    "controller_companion/app/res/tray_icon_dark_16.png"
)
XBOX_CONTROLLER_LAYOUT = __get_resource_path(
    "controller_companion/app/res/xbox_controller_layout.png"
)
PLAYSTATION_CONTROLLER_LAYOUT = __get_resource_path(
    "controller_companion/app/res/playstation_controller_layout.png"
)
PLUS_ICON = __get_resource_path("controller_companion/app/res/plus.png")
XBOX_BUTTONS_DEFAULT_DIR = __get_resource_path(
    "controller_companion/app/res/xbox/default"
)
XBOX_BUTTONS_LIGHT_DIR = __get_resource_path(
    "controller_companion/app/res/xbox/light"
)
PLAYSTATION_BUTTONS_DEFAULT_DIR = __get_resource_path(
    "controller_companion/app/res/playstation/default"
)
PLAYSTATION_BUTTONS_LIGHT_DIR = __get_resource_path(
    "controller_companion/app/res/playstation/light"
)
