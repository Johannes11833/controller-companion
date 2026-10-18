import argparse
import json
import os
import signal
import subprocess
from pathlib import Path
import sys
import webbrowser
from typing import List

import requests
from PIL import Image
from PySide6.QtCore import QSettings, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

import controller_companion
from controller_companion.app.autostart import (
    autostart_supported,
    get_autostart_enabled,
    set_auto_start,
)
from controller_companion.app.controller_layouts import ControllerType, get_layout
from controller_companion.app.utils import (
    OperatingSystem,
    combine_images_horizontally,
    get_os,
    invert_glyph,
    is_dark_appearance,
    pil_to_qpixmap,
    prettify_controller_name,
    set_window_icon,
    solid_silhouette,
)
from controller_companion.app.widgets.icon_delegate import IconDelegate
from controller_companion.app.widgets.popup_menu_widgets import PopupMenuTreeWidget
from controller_companion.controller import Controller
from controller_companion.logs import logger
from controller_companion.mapping import Mapping
from controller_companion.app import resources
from controller_companion.app.popup_about import AboutScreen
from controller_companion.app.popup_create_action import CreateActionPopup
import controller_companion.controller_observer as controller_observer


class ControllerCompanion(QMainWindow):
    # The controller observer runs in its own thread, so this signal is used to
    # marshal controller updates into the main thread (queued connection).
    controllers_changed = Signal(list)

    def __init__(self, launch_minimized=False):
        super().__init__()
        self.setWindowTitle(controller_companion.APP_NAME)
        set_window_icon(self)

        self.settings_file = controller_companion.CONFIG_PATH
        self.quit_requested = False
        self.observer = None

        # ui settings managed by Qt (e.g. window geometry); this is kept separate
        # from the app config file
        self.ui_settings = QSettings("controller-companion", "ui")

        # load settings
        self.settings = self.load_settings()

        self.controllers: List[Controller] = []
        self.rowheight = 30

        self.build_actions()
        self.build_menu()
        self.build_main_window()
        self.setup_tray_icon()

        # rebuild the mapping icons when the system switches between light and
        # dark mode while the app is running
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            self.on_color_scheme_changed
        )
        # colorSchemeChanged arrives before the new palette is applied, so also
        # refresh the stylesheet colors once the palette has actually changed
        QGuiApplication.instance().paletteChanged.connect(self.refresh_styled_widgets)

        # make sure UI updates from the observer thread are executed in the main thread
        self.controllers_changed.connect(self.update_controller_ui)

        # -------------------- start the joystick observer thread -------------------- #
        self.observer = controller_observer.ControllerObserver()
        self.observer.start_detached(
            defined_actions=self.defined_actions,
            debug=self.settings.get("debug", False),
            controller_callback=self.controllers_changed.emit,
            disabled_controllers=self.settings["disabled_controllers"],
        )
        # ---------------------------------------------------------------------------- #

        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        geometry = self.ui_settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        else:
            self.resize(900, 520)

        if launch_minimized:
            # use a timer so the window is fully initialized before hiding it
            QTimer.singleShot(100, lambda: self.minimize_to_tray(is_launch=True))

    def build_actions(self):
        # the mapping actions are shared between the File and Actions menus, the
        # context menu and the keyboard shortcuts, so they are created once here
        self.action_add_mapping = QAction("Add mapping", self)
        self.action_add_mapping.setShortcut(QKeySequence("Ctrl+N"))
        self.action_add_mapping.triggered.connect(self.open_add_actions)

        self.action_edit_mapping = QAction("Edit mapping", self)
        self.action_edit_mapping.setShortcut(QKeySequence("F2"))
        self.action_edit_mapping.triggered.connect(self.edit_action)

        self.action_duplicate_mapping = QAction("Duplicate mapping", self)
        self.action_duplicate_mapping.setShortcut(QKeySequence("Ctrl+D"))
        self.action_duplicate_mapping.triggered.connect(self.duplicate_action)

        self.action_delete_mapping = QAction("Delete mapping", self)
        self.action_delete_mapping.setShortcut(QKeySequence("Del"))
        self.action_delete_mapping.triggered.connect(self.delete_action)

    def build_menu(self):
        menu = self.menuBar()
        # tightly packed menu bar items
        menu.setStyleSheet(
            "QMenuBar::item { padding: 3px 6px; }"
            "QMenuBar::item:selected {"
            " background: palette(midlight);"
            " border-radius: 4px;"
            "}"
        )

        # File Menu
        file_menu = menu.addMenu("File")
        file_menu.addAction(self.action_add_mapping)
        file_menu.addAction(self.action_edit_mapping)
        file_menu.addAction(self.action_duplicate_mapping)
        file_menu.addAction(self.action_delete_mapping)

        file_menu.addSeparator()

        open_config = QAction("Open config file", self)
        open_config.setShortcut(QKeySequence("Ctrl+C"))
        open_config.triggered.connect(self.open_config)
        file_menu.addAction(open_config)

        file_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.quit_window)
        file_menu.addAction(quit_action)

        # Settings Menu
        settings_menu = menu.addMenu("Settings")
        self.action_minimize_on_close = QAction("Minimize to system tray", self)
        self.action_minimize_on_close.setCheckable(True)
        self.action_minimize_on_close.setChecked(self.settings["minimize_on_exit"])
        self.action_minimize_on_close.toggled.connect(self.save_settings)
        settings_menu.addAction(self.action_minimize_on_close)

        if (
            resources.is_frozen() and autostart_supported()
        ):  # only display auto start option if this is an executable
            self.action_auto_start = QAction("Auto Start", self)
            self.action_auto_start.setCheckable(True)
            self.action_auto_start.setChecked(get_autostart_enabled())
            self.action_auto_start.toggled.connect(self.toggle_autostart)
            settings_menu.addAction(self.action_auto_start)

        # Actions menu: quick access to all mapping actions; these are the same
        # QActions that the File menu and the context menu use
        actions_menu = menu.addMenu("Actions")
        actions_menu.addAction(self.action_add_mapping)
        actions_menu.addAction(self.action_edit_mapping)
        actions_menu.addAction(self.action_duplicate_mapping)
        actions_menu.addAction(self.action_delete_mapping)

        # Help Menu
        help_menu = menu.addMenu("Help")
        check_updates = QAction("Check for Updates", self)
        check_updates.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_updates)

        about = QAction("About", self)
        about.triggered.connect(self.open_about)
        help_menu.addAction(about)

        # search box in the top-right corner of the menu bar; the container keeps
        # the field away from the window edges
        corner_container = QWidget(self.menuBar())
        corner_layout = QHBoxLayout(corner_container)
        corner_layout.setContentsMargins(0, 3, 8, 3)

        self.filter_box = QLineEdit(corner_container)
        self.filter_box.setPlaceholderText("Filter mappings…")
        self.filter_box.setClearButtonEnabled(True)
        self.filter_box.setFixedWidth(150)
        self.filter_box.setStyleSheet(
            "QLineEdit {"
            " border: 1px solid palette(mid);"
            " border-radius: 4px;"
            " padding: 1px 6px;"
            " background: palette(base);"
            "}"
            "QLineEdit:focus { border: 1px solid palette(highlight); }"
        )
        self.filter_box.textChanged.connect(self.apply_filter)
        corner_layout.addWidget(self.filter_box)

        self.menuBar().setCornerWidget(corner_container, Qt.Corner.TopRightCorner)

    def build_main_window(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # ------------------------------- mappings table ------------------------------- #
        self.treeview = PopupMenuTreeWidget(
            central_widget,
            menu_actions={
                "add mapping": self.open_add_actions,
                "edit mapping": self.edit_action,
                "duplicate mapping": self.duplicate_action,
                "delete mapping(s)": self.delete_action,
            },
        )
        self.treeview.setHeaderLabels(["Shortcut", "Name", "Action", "Target"])
        self.treeview.setRootIsDecorated(False)
        self.treeview.setAllColumnsShowFocus(True)
        self.treeview.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.shortcut_delegate = IconDelegate(
            row_height=self.rowheight, parent=self.treeview
        )
        self.treeview.setItemDelegateForColumn(0, self.shortcut_delegate)
        # the shortcut column is always sized to exactly fit its icons and
        # cannot be resized by the user
        self.treeview.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.treeview.setColumnWidth(1, 170)
        self.treeview.setColumnWidth(2, 150)
        self.treeview.header().setStretchLastSection(True)
        self.treeview.itemSelectionChanged.connect(self.update_action_states)
        self.treeview.itemDoubleClicked.connect(lambda *_: self.edit_action())

        # hint overlay that is shown while the table is empty (or filtered empty)
        self.empty_label = QLabel(central_widget)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: gray;")

        self.mappings_stack = QStackedWidget(central_widget)
        self.mappings_stack.addWidget(self.treeview)
        self.mappings_stack.addWidget(self.empty_label)
        layout.addWidget(self.mappings_stack, 1)
        self.update_mappings_ui()

        # --------------------------- connected controllers --------------------------- #
        controllers_strip = QWidget(central_widget)
        self.controllers_strip_layout = QHBoxLayout(controllers_strip)
        self.controllers_strip_layout.setContentsMargins(0, 0, 0, 0)
        self.controllers_strip_layout.setSpacing(8)
        layout.addWidget(controllers_strip)

        self.update_controller_ui([])

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.update_tray_icon()
        self.tray_icon.setToolTip(
            f"{controller_companion.APP_NAME} {controller_companion.VERSION}"
        )

        tray_menu = QMenu(self)
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_window)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        # keep the tray icon visible for the whole lifetime of the app, even
        # while the window is shown
        self.tray_icon.setVisible(True)

    def tray_icon_path(self):
        """The tray icon variant that contrasts with the current taskbar."""
        if get_os() == OperatingSystem.LINUX:
            # on linux this will look very distorted on resolutions >16x16
            white_icon = resources.APP_ICON_PNG_TRAY_16
            dark_icon = resources.APP_ICON_PNG_TRAY_16_DARK
        else:
            white_icon = resources.APP_ICON_PNG_TRAY_32
            dark_icon = resources.APP_ICON_PNG_TRAY_32_DARK
        # the white glyph is for dark taskbars, the dark one for light taskbars
        return white_icon if is_dark_appearance() else dark_icon

    def update_tray_icon(self):
        self.tray_icon.setIcon(QIcon(str(self.tray_icon_path())))

    def on_color_scheme_changed(self, _=None):
        """Re-render the theme-dependent widgets for the new appearance."""
        self.update_mappings_ui()
        self.update_tray_icon()
        # the new palette is applied after this signal is handled; refresh the
        # styled widgets on the next event loop pass to pick it up reliably
        QTimer.singleShot(0, self.refresh_styled_widgets)

    def refresh_styled_widgets(self, _=None):
        """Re-apply theme-dependent styles after a palette change.

        Stylesheets resolve palette(...) references only once, when they are
        applied, so the filter box, menu bar and controller chips have to be
        refreshed after a theme switch.
        """
        self.filter_box.setStyleSheet(self.filter_box.styleSheet())
        menu = self.menuBar()
        menu.setStyleSheet(menu.styleSheet())
        # rebuilding the chips also updates their glyphs for the new mode
        self.update_controller_ui(self.controllers)

    def update_mappings_ui(self):
        self.treeview.clear()
        dpr = self.devicePixelRatioF()
        icon_size = (
            round((self.rowheight - 5) * dpr),
            round((self.rowheight - 5) * dpr),
        )
        layout_icons = {
            controller: get_layout(controller).get_button_icons(icon_size=icon_size)
            for controller in ControllerType
        }
        plus_icon = Image.open(resources.PLUS_ICON).resize(
            (
                round(self.rowheight // 3 * dpr),
                round(self.rowheight // 3 * dpr),
            )
        )

        # the plus glyph is dark; invert it so it stays readable on dark
        # backgrounds
        if is_dark_appearance():
            plus_icon = invert_glyph(plus_icon)

        max_width_shortcut = 0
        for mapping in self.defined_actions:
            icons = []
            for btn in mapping.active_controller_buttons:
                icons.append(layout_icons[mapping.controller_type][btn])
                icons.append(plus_icon)
            icons.pop()

            shortcut_pixmap = pil_to_qpixmap(
                combine_images_horizontally(
                    images=icons, height=round(self.rowheight * dpr)
                )
            )
            shortcut_pixmap.setDevicePixelRatio(dpr)
            max_width_shortcut = max(
                max_width_shortcut, shortcut_pixmap.deviceIndependentSize().width()
            )

            item = QTreeWidgetItem(
                self.treeview,
                [
                    "",
                    mapping.name,
                    mapping.action_type.value,
                    mapping.target,
                ],
            )
            item.setData(0, Qt.ItemDataRole.UserRole, shortcut_pixmap)

        # exactly fit the widest shortcut image (including the delegate's padding)
        self.treeview.setColumnWidth(
            0, round(max_width_shortcut) + 2 * self.shortcut_delegate.padding
        )

        self.apply_filter()

    def apply_filter(self, _=None):
        """Hide mappings that do not match the filter text and show an overlay hint
        while the table has nothing to show."""
        filter_text = self.filter_box.text().strip().lower()

        visible = 0
        for i in range(self.treeview.topLevelItemCount()):
            item = self.treeview.topLevelItem(i)
            mapping = self.defined_actions[i]
            haystack = " ".join(
                (
                    mapping.name,
                    mapping.target,
                    mapping.action_type.value,
                    mapping.controller_type.value,
                    mapping.get_shortcut_string(),
                )
            ).lower()

            matches = filter_text in haystack
            item.setHidden(not matches)
            visible += int(matches)

        if len(self.defined_actions) == 0:
            self.empty_label.setText(
                "No mappings yet.\nPress Ctrl+N or right-click to add one."
            )
            self.mappings_stack.setCurrentWidget(self.empty_label)
        elif visible == 0:
            self.empty_label.setText("No mappings match your filter.")
            self.mappings_stack.setCurrentWidget(self.empty_label)
        else:
            self.mappings_stack.setCurrentWidget(self.treeview)

        self.update_action_states()

    def update_action_states(self):
        """Enable the mapping actions depending on the current selection."""
        selected = len(self.treeview.selectedItems())
        self.action_edit_mapping.setEnabled(selected == 1)
        self.action_duplicate_mapping.setEnabled(selected == 1)
        self.action_delete_mapping.setEnabled(selected >= 1)

    def closeEvent(self, event: QCloseEvent):
        if (
            self.action_minimize_on_close.isChecked()
            and QSystemTrayIcon.isSystemTrayAvailable()
        ):
            self.minimize_to_tray()
            event.ignore()
        else:
            self.quit_window()
            event.accept()

    def minimize_to_tray(self, is_launch: bool = False):
        if not is_launch and not self.action_minimize_on_close.isChecked():
            # exit the app instead, as minimize to system tray is disabled
            self.quit_window()
            return

        if not QSystemTrayIcon.isSystemTrayAvailable():
            # without a system tray the window could not be restored, so keep it open
            logger.warning("System tray is not available; keeping the window open.")
            return

        self._save_geometry()
        self.hide()
        self.tray_icon.setVisible(True)

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window()

    def quit_window(self, _=None):
        self.quit_requested = True
        self._save_geometry()
        if self.observer is not None:
            self.observer.stop()
        if getattr(self, "tray_icon", None) is not None:
            self.tray_icon.setVisible(False)
        QApplication.instance().quit()

    def _save_geometry(self):
        self.ui_settings.setValue("geometry", self.saveGeometry())

    def show_window(self, _=None):
        self.show()
        self.raise_()
        self.activateWindow()

    def open_add_actions(self, _=None):
        popup = CreateActionPopup(self)
        popup.exec()
        if popup.result is not None:
            self.defined_actions.append(popup.result)
            self.update_mappings_ui()
            self.filter_box.clear()
            self.treeview.setCurrentItem(
                self.treeview.topLevelItem(len(self.defined_actions) - 1)
            )
            self.save_settings()

    def edit_action(self, _=None):
        items = self.treeview.selectedItems()
        if len(items) != 1:
            return

        idx = self.treeview.indexOfTopLevelItem(items[0])
        popup = CreateActionPopup(
            self, mapping=self.defined_actions[idx], title="Edit Action"
        )
        popup.exec()
        if popup.result is not None:
            self.defined_actions[idx] = popup.result
            self.update_mappings_ui()
            self.treeview.setCurrentItem(self.treeview.topLevelItem(idx))
            self.save_settings()

    def duplicate_action(self, _=None):
        items = self.treeview.selectedItems()
        if len(items) != 1:
            return

        idx = self.treeview.indexOfTopLevelItem(items[0])
        source = self.defined_actions[idx]
        duplicate = Mapping(
            action_type=source.action_type,
            target=source.target,
            active_controller_buttons=list(source.active_controller_buttons),
            name=f"{source.name} (copy)",
            controller_type=source.controller_type,
        )
        popup = CreateActionPopup(self, mapping=duplicate, title="Duplicate Action")
        popup.exec()
        if popup.result is not None:
            self.defined_actions.append(popup.result)
            self.update_mappings_ui()
            self.filter_box.clear()
            self.treeview.setCurrentItem(
                self.treeview.topLevelItem(len(self.defined_actions) - 1)
            )
            self.save_settings()

    def delete_action(self, _=None):
        selection = self.treeview.selectedItems()
        # remove the mappings in reverse order so the indices stay valid
        for idx in sorted(
            (self.treeview.indexOfTopLevelItem(item) for item in selection),
            reverse=True,
        ):
            self.defined_actions.pop(idx)
        self.update_mappings_ui()

        if len(selection) > 0:
            self.save_settings()

    def update_controller_ui(self, controllers: List[Controller]):
        self.controllers = controllers

        # remove the old chips; detach them immediately so they cannot linger
        # visible on top of the rebuilt ones until deleteLater() fires
        while self.controllers_strip_layout.count() > 0:
            item = self.controllers_strip_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        if not controllers:
            label = QLabel("Controllers: none connected")
            label.setEnabled(False)
            self.controllers_strip_layout.addWidget(label)
            self.controllers_strip_layout.addStretch()
            return

        self.controllers_strip_layout.addWidget(QLabel("Controllers:"))

        show_numbers = len(controllers) > 1
        for i, c in enumerate(controllers):
            label = f"{prettify_controller_name(c.name)} Controller"
            if show_numbers:
                # only disambiguate when several controllers are connected
                label = f"{label} {i + 1}"
            chip = QPushButton(label)
            chip.setCheckable(True)
            chip.setChecked(c.guid not in self.settings["disabled_controllers"])
            chip.setToolTip("Click to enable/disable this controller")
            self.set_chip_icon(chip, c)
            chip.setStyleSheet(
                "QPushButton {"
                " padding: 2px 10px;"
                " border: 1px solid palette(mid);"
                " border-radius: 10px;"
                "}"
                "QPushButton:checked {"
                " background: palette(highlight);"
                " color: white;"
                " border-color: palette(highlight);"
                "}"
                "QPushButton:!checked {"
                " color: palette(mid);"
                "}"
            )
            chip.toggled.connect(
                lambda checked, guid=c.guid: self.toggle_controller(guid, checked)
            )
            self.controllers_strip_layout.addWidget(chip)

        self.controllers_strip_layout.addStretch()

    def set_chip_icon(self, chip: QPushButton, controller: Controller):
        """Puts a small silhouette glyph of the controller family on the chip.

        White while the controller is enabled (accent-colored chip) and muted
        while it is disabled.
        """
        glyph_path = controller.layout.get_chip_icon_path()
        if glyph_path is None or not glyph_path.is_file():
            return

        glyph = Image.open(glyph_path).resize((32, 32))
        muted = self.palette().mid().color()
        off_icon = QIcon(
            pil_to_qpixmap(
                solid_silhouette(glyph, (muted.red(), muted.green(), muted.blue(), 255))
            )
        )
        on_icon = QIcon(
            pil_to_qpixmap(solid_silhouette(glyph, (255, 255, 255, 255)))
        )
        chip.setIconSize(QSize(16, 16))
        chip.setIcon(on_icon if chip.isChecked() else off_icon)
        chip.toggled.connect(
            lambda checked, c=chip, on=on_icon, off=off_icon: c.setIcon(
                on if checked else off
            )
        )

    def toggle_controller(self, guid: str, enabled: bool):
        # the disabled_controllers list object is shared with the observer thread,
        # so it must be modified in place
        disabled_controllers = self.settings["disabled_controllers"]

        if enabled and guid in disabled_controllers:
            disabled_controllers.remove(guid)
        elif not enabled and guid not in disabled_controllers:
            disabled_controllers.append(guid)

        self.save_settings()

    def load_settings(self):
        settings = {
            "minimize_on_exit": True,
            "debug": False,
            "disabled_controllers": [],
        }

        if self.settings_file.is_file():
            try:
                settings.update(json.loads(self.settings_file.read_text()))
                self.defined_actions = [
                    Mapping.from_dict(d) for d in settings["actions"]
                ]
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Config File Error",
                    f"Failed to load the config file.\nError message: {str(e)}",
                )
                self.open_config()
                self.quit_window()
        else:
            self.defined_actions = []

        return settings

    def open_config(self, _=None):
        if not self.settings_file.is_file():
            self.save_settings()

        if sys.platform == "win32":
            os.startfile(self.settings_file)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, self.settings_file])

    def save_settings(self, _=None):
        # update the settings dict
        self.settings.update(
            {
                "minimize_on_exit": self.action_minimize_on_close.isChecked(),
                "actions": [item.to_dict() for item in self.defined_actions],
            }
        )
        self.settings_file.parent.mkdir(exist_ok=True, parents=True)
        self.settings_file.write_text(json.dumps(self.settings, indent=4))

        logger.debug(f"Saved settings to: {self.settings_file}")

    def toggle_autostart(self, enabled: bool):
        set_auto_start(enable=enabled)
        self.save_settings()

    def open_about(self, _=None):
        AboutScreen(self).exec()

    def check_for_updates(self, _=None):
        response = requests.get(
            "https://api.github.com/repos/Johannes11833/controller-companion/releases/latest"
        )
        latest_version = response.json()["name"]
        installed_version = controller_companion.VERSION

        if latest_version == installed_version:
            QMessageBox.information(
                self,
                "Up to date",
                f"The latest version of {controller_companion.APP_NAME} is installed.",
            )
        else:
            url = (
                "https://github.com/Johannes11833/controller-companion/releases/latest"
            )
            logger.info(
                f"A new update is available: {installed_version} -> {latest_version}. URL: {url}"
            )
            open_website = QMessageBox.question(
                self,
                f"Update available: {latest_version}",
                f"A new update is available for {controller_companion.APP_NAME}. Go to download page now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if open_website == QMessageBox.StandardButton.Yes:
                webbrowser.open_new_tab(
                    url,
                )


def launch_app(minimized: bool = False):
    pid_file = Path(controller_companion.PID_PATH)
    if pid_file.is_file():
        pid_running = int(pid_file.read_text())
        try:
            # kill the running instance
            # (might fail if it is not running but .pid file exists)
            os.kill(
                pid_running,
                (
                    signal.SIGTERM
                    if get_os() == OperatingSystem.WINDOWS
                    else signal.SIGKILL
                ),
            )
        except OSError:
            logger.warning("Failed to kill running instance!")
    pid_current = os.getpid()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid_current))

    # launch the app
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName(controller_companion.APP_NAME)
        # the app must not exit when the window is hidden to the system tray
        app.setQuitOnLastWindowClosed(False)

    window = ControllerCompanion(launch_minimized=minimized)
    if window.quit_requested:
        # the window requested to be closed during initialization
        # (e.g. because of an invalid config file)
        pid_file.unlink(missing_ok=True)
        return

    window.show()
    app.exec()

    # remove the pid file if the app is exited by the user
    pid_file.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Lauch the {controller_companion.APP_NAME} UI App."
    )
    parser.add_argument(
        "-m",
        "--minimized",
        help="Launch minimized.",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()

    launch_app(minimized=args.minimized)
