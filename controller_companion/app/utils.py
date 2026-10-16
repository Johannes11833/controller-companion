from enum import Enum
import platform
from typing import List, Tuple

from PIL import Image, ImageFilter, ImageOps
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


def add_silhouette_border(
    image: Image.Image, color: Tuple[int, int, int, int], thickness: int = 1
) -> Image.Image:
    """Draws a solid border around the opaque silhouette of the image.

    The alpha mask is grown by ``thickness`` pixels in every direction and the
    grown area is filled with ``color``, giving the dark glyph artwork a
    visible outline on backgrounds of any brightness. The returned image is
    ``2 * thickness`` pixels larger than the input in each dimension.
    """
    image = image.convert("RGBA")
    canvas = Image.new(
        "RGBA",
        (image.width + 2 * thickness, image.height + 2 * thickness),
        (0, 0, 0, 0),
    )
    canvas.paste(image, (thickness, thickness))

    grown = canvas.getchannel("A").filter(ImageFilter.MaxFilter(2 * thickness + 1))
    border = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    border.paste(Image.new("RGBA", canvas.size, color), (0, 0), grown)
    return Image.alpha_composite(border, canvas)


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
