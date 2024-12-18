from enum import Enum
import platform
from tkinter import Tk
from PIL import Image, ImageTk

from controller_companion.app import resources


def set_window_icon(root: Tk):
    im = Image.open(resources.APP_ICON_ICO)
    photo = ImageTk.PhotoImage(im)
    root.wm_iconphoto(True, photo)


class OperatingSystem(Enum):
    WINDOWS = "Windows"
    MAC = "Darwin"
    LINUX = "Linux"


def get_os() -> OperatingSystem:
    return OperatingSystem(platform.system())
