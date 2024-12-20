from enum import Enum
import platform
from tkinter import Tk
from PIL import Image, ImageTk

from controller_companion.app import resources


def set_window_icon(root: Tk):
    im = Image.open(resources.APP_ICON_PNG)
    photo_32 = ImageTk.PhotoImage(im)
    photo_16 = ImageTk.PhotoImage(im.resize(size=(16, 16)))
    root.iconphoto(False, photo_32, photo_16)


class OperatingSystem(Enum):
    WINDOWS = "Windows"
    MAC = "Darwin"
    LINUX = "Linux"


def get_os() -> OperatingSystem:
    return OperatingSystem(platform.system())
