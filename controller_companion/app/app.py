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
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
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
    pil_to_qpixmap,
    set_window_icon,
)
from controller_companion.app.widgets.icon_delegate import IconDelegate
from controller_companion.app.widgets.popup_menu_widgets import (
    PopupMenuListWidget,
    PopupMenuTreeWidget,
)
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

        # load settings
        self.settings = self.load_settings()

        self.controllers: List[Controller] = []
        self.rowheight = 30

        self.build_menu()
        self.build_main_window()
        self.setup_tray_icon()

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

        self.resize(500, 700)

        if launch_minimized:
            # use a timer so the window is fully initialized before hiding it
            QTimer.singleShot(100, lambda: self.minimize_to_tray(is_launch=True))

    def build_menu(self):
        menu = self.menuBar()

        # File Menu
        file_menu = menu.addMenu("File")

        add_mapping = QAction("Add mapping", self)
        add_mapping.setShortcut(QKeySequence("Ctrl+N"))
        add_mapping.triggered.connect(self.open_add_actions)
        file_menu.addAction(add_mapping)

        delete_mapping = QAction("Delete mapping", self)
        delete_mapping.setShortcut(QKeySequence("Del"))
        delete_mapping.triggered.connect(self.delete_action)
        file_menu.addAction(delete_mapping)

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

        # Help Menu
        help_menu = menu.addMenu("Help")
        check_updates = QAction("Check for Updates", self)
        check_updates.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_updates)

        about = QAction("About", self)
        about.triggered.connect(self.open_about)
        help_menu.addAction(about)

    def build_main_window(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # ------------------------------- mappings table ------------------------------- #
        layout.addWidget(QLabel("Defined Mappings", central_widget))

        self.treeview = PopupMenuTreeWidget(
            central_widget,
            menu_actions={"delete mapping(s)": self.delete_action},
        )
        self.treeview.setHeaderLabels(["Shortcut", "Name", "Target"])
        self.treeview.setRootIsDecorated(False)
        self.treeview.setAllColumnsShowFocus(True)
        self.treeview.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.treeview.setItemDelegateForColumn(
            0, IconDelegate(row_height=self.rowheight, parent=self.treeview)
        )
        self.treeview.header().setStretchLastSection(True)
        layout.addWidget(self.treeview, 1)
        self.update_mappings_ui()

        # --------------------------- connected controllers --------------------------- #
        layout.addWidget(QLabel("Connected Controllers", central_widget))
        self.listbox_controllers = PopupMenuListWidget(
            central_widget,
            menu_actions={"toggle on/off": self.toggle_controller},
        )
        self.listbox_controllers.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        layout.addWidget(self.listbox_controllers, 1)

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        if get_os() == OperatingSystem.LINUX:
            # on linux this will look very distorted on resolutions >16x16
            image_path = resources.APP_ICON_PNG_TRAY_16
        else:
            image_path = resources.APP_ICON_PNG_TRAY_32
        self.tray_icon.setIcon(QIcon(str(image_path)))
        self.tray_icon.setToolTip(controller_companion.APP_NAME)

        tray_menu = QMenu(self)
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_window)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.setVisible(False)

    def update_mappings_ui(self):
        self.treeview.clear()
        icon_size = (self.rowheight - 5, self.rowheight - 5)
        layout_icons = {
            controller: get_layout(controller).get_button_icons(icon_size=icon_size)
            for controller in ControllerType
        }
        plus_icon = Image.open(resources.PLUS_ICON).resize(
            (self.rowheight // 3, self.rowheight // 3)
        )

        max_width_shortcut = 0
        for mapping in self.defined_actions:
            icons = []
            for btn in mapping.active_controller_buttons:
                icons.append(layout_icons[mapping.controller_type][btn])
                icons.append(plus_icon)
            icons.pop()

            shortcut_pixmap = pil_to_qpixmap(
                combine_images_horizontally(images=icons, height=self.rowheight)
            )
            max_width_shortcut = max(max_width_shortcut, shortcut_pixmap.width())

            item = QTreeWidgetItem(
                self.treeview, ["", mapping.name, mapping.target]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, shortcut_pixmap)

        # make sure the width of the first column is large enough to fit the shortcut images
        self.treeview.setColumnWidth(0, max_width_shortcut + 30)

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
        if self.observer is not None:
            self.observer.stop()
        if getattr(self, "tray_icon", None) is not None:
            self.tray_icon.setVisible(False)
        QApplication.instance().quit()

    def show_window(self, _=None):
        self.tray_icon.setVisible(False)
        self.show()
        self.raise_()
        self.activateWindow()

    def open_add_actions(self, _=None):
        popup = CreateActionPopup(self)
        popup.exec()
        if popup.result is not None:
            self.defined_actions.append(popup.result)
            self.update_mappings_ui()
            self.save_settings()

    def delete_action(self, _=None):
        selection = self.treeview.selectedItems()
        # remove the mappings in reverse order so the indices stay valid
        for idx in sorted(
            (
                self.treeview.indexOfTopLevelItem(item)
                for item in selection
            ),
            reverse=True,
        ):
            self.defined_actions.pop(idx)
        self.update_mappings_ui()

        if len(selection) > 0:
            self.save_settings()

    def update_controller_ui(self, controllers: List[Controller]):
        self.controllers = controllers

        self.listbox_controllers.clear()
        for i, c in enumerate(controllers):
            item = f"Controller {i+1}: {c.name}"

            if c.guid in self.settings["disabled_controllers"]:
                item += "  [disabled]"

            self.listbox_controllers.addItem(item)

    def toggle_controller(self, _=None):
        disabled_controllers = self.settings["disabled_controllers"]
        selected_idcs = [
            item.row() for item in self.listbox_controllers.selectedIndexes()
        ]
        selected_guids = set([self.controllers[i].guid for i in selected_idcs])

        # selected controllers that are currently enabled/ disabled
        selected_disabled_guids = set(disabled_controllers) & selected_guids
        selected_enabled_guids = selected_guids - selected_disabled_guids

        # toggle: disabled controllers ---> enabled and vice versa
        new_disabled = list(
            (set(disabled_controllers) | selected_enabled_guids)
            - selected_disabled_guids
        )
        disabled_controllers.clear()
        disabled_controllers.extend(new_disabled)

        self.update_controller_ui(self.controllers)
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
