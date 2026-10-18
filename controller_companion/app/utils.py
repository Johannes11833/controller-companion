from enum import Enum
import platform
from typing import List, Tuple

from PIL import Image, ImageOps
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPalette, QPixmap
from PySide6.QtWidgets import QWidget

from controller_companion.app import resources


def set_window_icon(window: QWidget):
    window.setWindowIcon(QIcon(str(resources.APP_ICON_PNG)))


def is_dark_appearance() -> bool:
    """Whether the application is currently drawn with a dark color scheme."""
    app = QGuiApplication.instance()
    if app is None:
        return False
    scheme = app.styleHints().colorScheme()
    if scheme == Qt.ColorScheme.Dark:
        return True
    if scheme == Qt.ColorScheme.Light:
        return False
    # some platforms never report a color scheme; fall back to the palette
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


def invert_glyph(image: Image.Image) -> Image.Image:
    """Inverts the colors of a dark glyph image while keeping its transparency.

    The controller assets are drawn in dark colors for light backgrounds; the
    inverted variant keeps them readable on dark backgrounds.
    """
    image = image.convert("RGBA")
    alpha = image.getchannel("A")
    inverted = ImageOps.invert(image.convert("RGB")).convert("RGBA")
    inverted.putalpha(alpha)
    return inverted


def solid_silhouette(
    image: Image.Image, color: Tuple[int, int, int, int]
) -> Image.Image:
    """Fills the opaque shape of the image with a solid color."""
    image = image.convert("RGBA")
    silhouette = Image.new("RGBA", image.size, color)
    silhouette.putalpha(image.getchannel("A"))
    return silhouette


def prettify_controller_name(name: str) -> str:
    """Maps verbose device names to a friendly hardware-family name.

    Controllers usually report long, vendor-specific names (e.g. "Xbox One
    For Windows"); this keeps the recognizable part only. Unknown names are
    returned unchanged.
    """
    lower = name.lower()
    for needle, pretty in (
        ("xbox one", "Xbox One"),
        ("xbox series", "Xbox Series"),
        ("xbox 360", "Xbox 360"),
        ("xbox", "Xbox"),
        ("dualsense", "DualSense"),
        ("dualshock", "DualShock"),
        ("playstation", "PlayStation"),
        ("ps5", "PlayStation 5"),
        ("ps4", "PlayStation 4"),
        ("ps3", "PlayStation 3"),
        # many PlayStation pads report this generic name on Windows
        ("wireless controller", "PlayStation"),
    ):
        if needle in lower:
            return pretty
    return name


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
