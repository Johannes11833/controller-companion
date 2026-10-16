from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLayout,
    QVBoxLayout,
)

import controller_companion
from controller_companion.app import resources
from controller_companion.app.utils import set_window_icon


class AboutScreen(QDialog):
    def __init__(self, master=None):
        super().__init__(master)
        self.setWindowTitle("About")
        set_window_icon(self)

        layout = QHBoxLayout(self)

        icon_label = QLabel(self)
        icon_label.setPixmap(
            QPixmap(str(resources.APP_ICON_PNG)).scaled(
                50,
                50,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(icon_label)

        info_layout = QVBoxLayout()
        title_label = QLabel(
            f"{controller_companion.APP_NAME} {controller_companion.VERSION}",
            self,
        )
        font = title_label.font()
        font.setPointSize(12)
        font.setBold(True)
        title_label.setFont(font)
        info_layout.addWidget(title_label)

        info_layout.addWidget(QLabel("Made by Johannes Gundlach", self))

        link_label = QLabel(
            '<a href="https://github.com/Johannes11833/controller-companion">'
            "https://github.com/Johannes11833/controller-companion</a>",
            self,
        )
        link_label.setOpenExternalLinks(True)
        info_layout.addWidget(link_label)

        layout.addLayout(info_layout)

        # prevent the dialog from being resized
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
