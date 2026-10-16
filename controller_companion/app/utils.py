from enum import Enum
import platform
from typing import List

from PIL import Image
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QWidget

from controller_companion.app import resources


def set_window_icon(window: QWidget):
    window.setWindowIcon(QIcon(str(resources.APP_ICON_PNG)))


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """Converts a PIL image to a QPixmap."""
    image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(
        data,
        image.width,
        image.height,
        image.width * 4,
        QImage.Format.Format_RGBA8888,
    )
    # QImage does not take ownership of the data, so copy it onto a buffer owned by Qt
    return QPixmap.fromImage(qimage.copy())


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
