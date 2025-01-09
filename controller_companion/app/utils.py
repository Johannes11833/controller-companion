from enum import Enum
import platform
from tkinter import Tk
from typing import List
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


def combine_images_horizontally(
    images: List[Image.Image],
    height: int,
    center_vertically=True,
) -> Image.Image:
    total_width = sum([i.width for i in images])
    combined_icons = Image.new("RGBA", (total_width, height))
    x_offset = 0

    for im in images:
        y_offset = max(0, (height - im.height) // 2) if center_vertically else 0
        combined_icons.paste(im, (x_offset, y_offset))
        x_offset += im.size[0]

    return combined_icons
