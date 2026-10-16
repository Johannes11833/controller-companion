from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QStyledItemDelegate


class IconDelegate(QStyledItemDelegate):
    """Draws the QPixmap stored in the Qt.UserRole of the item data."""

    def __init__(self, row_height: int, padding: int = 6, parent=None):
        super().__init__(parent)
        self.row_height = row_height
        self.padding = padding

    def paint(self, painter, option, index):
        # let the base class draw the background (including the selection highlight)
        super().paint(painter, option, index)

        pixmap = index.data(Qt.ItemDataRole.UserRole)
        if pixmap is None or pixmap.isNull():
            return

        x = option.rect.x() + self.padding
        y = option.rect.y() + max(0, (option.rect.height() - pixmap.height()) // 2)
        painter.drawPixmap(x, y, pixmap)

    def sizeHint(self, option, index):
        pixmap = index.data(Qt.ItemDataRole.UserRole)
        width = pixmap.width() + 2 * self.padding if pixmap else 0
        return QSize(width, self.row_height)
