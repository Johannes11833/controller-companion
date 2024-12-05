from pathlib import Path
import sys


def __get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    # for executables, _MEIPASS is set, in dev mode we will use the repo root.
    base_path = getattr(sys, "_MEIPASS", "")
    print("BASE PATH", base_path)
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
