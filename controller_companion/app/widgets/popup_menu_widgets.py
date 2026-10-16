from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QMenu, QTreeWidget


def _add_popup_menu(
    widget, menu_actions: Optional[Dict[str, Callable[[], None]]] = None
):
    """Adds a context menu with the given actions to a view widget."""
    menu = QMenu(widget)
    for action_name, callback in (menu_actions or {}).items():
        menu.addAction(action_name, callback)

    widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    widget.customContextMenuRequested.connect(
        lambda pos: menu.exec(widget.mapToGlobal(pos))
    )


class PopupMenuListWidget(QListWidget):
    def __init__(
        self,
        parent,
        menu_actions: Optional[Dict[str, Callable[[], None]]] = None,
    ):
        super().__init__(parent)
        _add_popup_menu(self, menu_actions)


class PopupMenuTreeWidget(QTreeWidget):
    def __init__(
        self,
        parent,
        menu_actions: Optional[Dict[str, Callable[[], None]]] = None,
    ):
        super().__init__(parent)
        _add_popup_menu(self, menu_actions)
